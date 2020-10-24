import * as express from 'express';
import * as Git from 'nodegit';
import { c } from '../lib/Log';
import { Repo } from './Repo';
import { Utils } from '../lib/Utils';
import {
	NotFoundError,
	TreeContext,
	BlobContext,
	CommitContext,
	HistoryContext,
} from './Context';
import { TemplateInfo } from './TemplateInfo';





export const getLastCommit = async (
	repo: Git.Repository,
	path: string,
	before: Git.Commit,
): Promise<Git.Commit | undefined> => {
	const revWalk = repo.createRevWalk();
	revWalk.push(before.id());
	revWalk.sorting(Git.Revwalk.SORT.TIME);
	const last = (await revWalk.fileHistoryWalk(path, 1_000))[0];
	if (last && last.commit instanceof Git.Commit) {
		return last.commit;
	}
	return undefined;
};


export const indexTree: express.RequestHandler = async function(req, res) {
	const context = new TreeContext(req);
	try {
		await context.initialize();
	} catch(err) {
		if (err instanceof NotFoundError) {
			return res.status(404).send(`Not Found: ${err}`);
		}
	}
	
	const entries = context.tree.entries();
	
	const commitsLast = await Promise.all(entries.map(async x => {
		const l = await getLastCommit(context.repo, x.path(), context.commit);
		(<any>x).lastCommit = l;
		return l;
	}));
	const commitLast: Git.Commit | undefined = Utils.filterUndef(commitsLast)
		.sort((a, b) => b.time() - a.time())[0]
	;
	
	if (context.path === undefined) {
		const n = await Repo.numOfCommits(context.repo, context.commit);
		context.data.historyLink = `History: ${n} commits`;
	}
	
	res.render('index_tree', {
		info: await TemplateInfo.info(context, req.path),
		context,
		commitLast,
		dirs:  entries.filter(x => x.isTree()),
		files: entries.filter(x => x.isBlob()),
		layout: 'base',
	});
}


//#region blob
export const indexBlob: express.RequestHandler = async function(req, res) {
	const context = new BlobContext(req);
	try {
		await context.initialize();
	} catch(err) {
		if (err instanceof NotFoundError) {
			return res.status(404).send(`Not Found: ${err}`);
		}
	}
	
	const commitLast = await getLastCommit(context.repo, context.path!, context.commit);
	
	if (!context.isBinary && !context.isTooLarge) {
		context.renderText();
	}
	
	res.render('index_blob', {
		info: await TemplateInfo.info(context, req.path),
		context,
		commitLast,
		layout: 'base',
	});
};

export const rawBlob: express.RequestHandler = async function(req, res) {
	const context = new BlobContext(req);
	try {
		await context.initialize();
	} catch(err) {
		if (err instanceof NotFoundError) {
			return res.status(404).send(`Not Found: ${err}`);
		}
	}
	/// we don't really need to set a content-type.
	const type = "text/plain";
	res.set('content-type', type);
	res.send(context.blob.content());
};

export const blameBlob: express.RequestHandler = async function(req, res) {
	const context = new BlobContext(req);
	try {
		await context.initialize();
	} catch(err) {
		if (err instanceof NotFoundError) {
			return res.status(404).send(`Not Found: ${err}`);
		}
	}
	
	if (context.isBinary) {
		return res.status(404).send(`Not Found: Binary data`);
	}
	if (context.isTooLarge) {
		return res.status(404).send(`Not Found: File is too large`);
	}
	context.renderText();
	
	const line_commits: (Git.Oid | undefined)[] = [];
	let last_dedup: Git.Oid | undefined;
	const blame = await Git.Blame.file(context.repo, context.path!, {
		newestCommit: context.commit.id(),
	});
	for (let i = 0; i < blame.getHunkCount(); i++) {
		const hunk = blame.getHunkByIndex(i);
		if (hunk.finalCommitId().tostrS() !== last_dedup?.tostrS()) {
			last_dedup = hunk.finalCommitId();
			line_commits[hunk.finalStartLineNumber()] = hunk.finalCommitId();
		}
	}
	line_commits.shift();
	/// ^^ blame lines are 1-indexed.
	context.data.line_commits = line_commits.map(x => {
		if (x) {
			return `<a href="/${context.repoName}/commit/${x}">${ x.tostrS().substr(0, 7) }</a>`;
		} else {
			return `&nbsp;`
		}
	}).join("\n");
	
	res.render('blame_blob', {
		info: await TemplateInfo.info(context, req.path),
		context,
		line_commits,
		layout: 'base',
	});
}
//#endregion


export const viewCommit: express.RequestHandler = async function(req, res) {
	const context = new CommitContext(req);
	try {
		await context.initialize();
	} catch(err) {
		if (err instanceof NotFoundError) {
			return res.status(404).send(`Not Found: ${err}`);
		}
	}
	
	const diffList = await context.commit.getDiff();
	const diffStats = await Promise.all(diffList.map(async x => {
		const stats = await x.getStats();
		return `${stats.filesChanged()} changed files with ${stats.insertions()} additions and ${stats.deletions()} deletions`;
	}));
	
	/// copy/paste of
	/// github.com/nodegit/nodegit/blob/master/examples/diff-commits.js
	let outputDiff = "";
	for (const [i_diff, diff] of diffList.entries()) {
		outputDiff += `Diff #${i_diff}\n`;
		const patches = await diff.patches();
		for (const [i_patch, patch] of patches.entries()) {
			const hunks = await patch.hunks();
			for (const [i_hunk, hunk] of hunks.entries()) {
				const lines = await hunk.lines();
				outputDiff += `\n<strong>Patch #${i_patch}, Hunk #${i_hunk}</strong>\n`;
				outputDiff += `diff ${patch.oldFile().path()} ${patch.newFile().path()}\n`;
				outputDiff += hunk.header().trim() + '\n\n';
				
				outputDiff += `<small style="color: grey">` + lines.map(line => {
					return String.fromCharCode(line.origin()) + line.content().trim();
				}).join('\n') + `</small>\n`;
			}
		}
	}
	
	res.render('view_commit', {
		info: await TemplateInfo.info(context, req.path),
		context,
		diffStats,
		outputDiff,
		no_branch_selector: true,
		layout: 'base',
	});
}


export const historyCommits: express.RequestHandler = async function(req, res) {
	const context = new HistoryContext(req);
	try {
		await context.initialize();
	} catch(err) {
		if (err instanceof NotFoundError) {
			return res.status(404).send(`Not Found: ${err}`);
		}
	}
	
	const revWalk = context.repo.createRevWalk();
	revWalk.push(context.commit.id());
	const oids: Git.Oid[] = [];
	while (true) {
		try {
			const oid = await revWalk.next();
			oids.push(oid);
		} catch(err) {
			if (err.errno === Git.Error.CODE.ITEROVER) {
				break;
			}
			throw err;
		}
	}
	const allCommits = await Promise.all(oids.map(x => context.repo.getCommit(x)));
	/// ^^ this is very fast.
	/// no pagination (we haven't had the use for now.)
	let commits: Git.Commit[] = [];
	if (context.path === undefined) {
		commits = allCommits;
	} else {
		/// CAUTION(this can be pretty long)
		const startTime = Date.now();
		for (const commit of allCommits) {
			const diffList = await commit.getDiff();
			const patches = (await Promise.all(diffList.map(x => x.patches()))).flat();
			const touchedFiles = new Set(
				patches.map(x => (
					[x.oldFile().path(), x.newFile().path()]
				)).flat()
			);
			if (
				   touchedFiles.has(context.path)
				|| [...touchedFiles].some(fpath => fpath.startsWith(context.path+`/`))
			) {
				/// Handle both folder and path in one `if`
				commits.push(commit);
			}
		}
		c.log(
			`history.commits.filtered`,
			`[${context.repoName}]`,
			Date.now() - startTime
		);
	}
	
	res.render('history_commits', {
		info: await TemplateInfo.info(context, req.path),
		context,
		commits,
		layout: 'base',
	});
}

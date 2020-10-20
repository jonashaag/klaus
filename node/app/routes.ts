import * as express from 'express';
import * as Git from 'nodegit';
import * as hljs from 'highlight.js';
import { extname } from 'path';
import { c } from '../lib/Log';
import { Repo } from './Repo';
import { Utils } from '../lib/Utils';
import {
	TreeContext,
	BlobContext,
	NotFoundError,
} from './Context';





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
		refs: await Repo.refs(context.repo),
		context,
		commitLast,
		dirs:  entries.filter(x => x.isTree()),
		files: entries.filter(x => x.isBlob()),
		layout: 'base',
	});
}

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
		const ext = Utils.trimPrefix(extname(context.path!), ".");
		try {
			const res = hljs.highlight(ext, context.blob.toString(), true);
			context.data.code = res.value;
		} catch {
			/// Fallback to automatic detection.
			const res = hljs.highlightAuto(context.blob.toString());
			context.data.code = res.value;
		}
		c.debug(context.data.code);
	}
	
	res.render('index_blob', {
		refs: await Repo.refs(context.repo),
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

import * as util from 'util';
import * as child_process from 'child_process';
import * as Git from 'nodegit';
import * as express from 'express';
import { c } from './lib/Log';
import { hbs } from './lib/Hbs';
import __rootDir, { __klausDir, __nodeDir } from './lib/RootDirFinder';
import { Utils } from './lib/Utils';
import { Repo } from './app/Repo';
import { indexTree, indexBlob } from './app/routes';
const __exec = util.promisify(child_process.exec);

const app = express();
const PORT = process.env.PORT || 8888;


// Express setup
app.set('views', `${__nodeDir}/views`);
app.set('view engine', 'hbs');
app.engine('hbs', hbs.renderFile.bind(hbs));

app.use(
	'/static',
	express.static(`${__klausDir}/static`)
);
app.get(
	'/favicon.ico',
	(req, res) => res.sendFile(`${__klausDir}/static/favicon.png`)
);

/**
 * Note: we only support branch names and tag names
 * not containing a `/`.
 */

 
/**
 * Routes(html)
 */

app.get('/', async function(req, res) {
	const repoFolders = await Utils.readdirREnt(
		Repo.ROOT_REPOS,
		(x) => x.name.endsWith(`.git`),
		2
	);
	/// Assume top-level or nesting=1 folders in this dir
	/// are our repos.
	/// Also assume they are bare repos.
	const repos = await Promise.all(repoFolders.map(x => {
		return Git.Repository.openBare(x);
	}));
	const headCommits = await Promise.all(repos.map(x => x.getHeadCommit()));
	
	const items: {
		repo: Git.Repository,
		commit: Git.Commit,
	}[] = Utils.zip(repos, headCommits).map(x => ({ repo: x[0], commit: x[1] }));
	
	if (req.query['by-name']) {
		items.sort((a, b) => Repo.name(a.repo).localeCompare(Repo.name(b.repo)));
	} else {
		items.sort((a, b) => b.commit.time() - a.commit.time());
	}
	
	res.render('repo_list', {
		items,
		order_by: req.query['by-name'] ? 'name' : 'last_updated',
		meta: {
			title: `Repository list`,
		},
		layout: 'skeleton',
	});
});


app.get('/:repo',                        indexTree);
app.get('/:namespace/:repo',             indexTree);
app.get('/:repo/tree/:rev/*',            indexTree);
app.get('/:namespace/:repo/tree/:rev/*', indexTree);

// app.get('/:repo', async function(req, res) {
// 	/// Show commits of a branch, just like `git log`
// 	const context = await _get_repo_and_rev(req.params.repo);
// 	// const tree = await context.entry.getTree();
// 	const dirs  = context.tree.entries().filter(x => x.isTree());
// 	const files = context.tree.entries().filter(x => x.isBlob());
	
// 	const revWalk = context.repo.createRevWalk();
// 	revWalk.pushHead();
// 	const history = await revWalk.getCommits(50);
	
// 	res.render('index', {
// 		context,
// 		history,
// 		listdir: { dirs, files },
// 		layout: 'base',
// 	});
// });



app.get(           '/:repo/blob/:rev/*', indexBlob);
app.get('/:namespace/:repo/blob/:rev/*', indexBlob);



app.get('/:repo/commit/*/', async function(req, res) {
	const context = await _get_repo_and_rev(
		req.params.repo,
		Utils.trimSuffix(req.params[0], "/")
	);
	
	res.render('view_commit', {
		commit: context.commit,
		layout: 'base',
	});
});


// Start engine.

const guess_git_revision = async () => {
	try {
		const { stdout } = await __exec(`git log --format=%h -n 1`);
		return stdout.trim();
	} catch {
		return `1.5.2`;
	}
};

(async () => {
	app.locals.KLAUS_VERSION = await guess_git_revision();
	app.locals.SITE_NAME = process.env.KLAUS_SITE_NAME ?? "klaus-node";
	
	app.listen(PORT, () => {
		c.debug(`Running on http://localhost:${PORT}`);
	});
})();

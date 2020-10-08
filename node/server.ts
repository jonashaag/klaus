import * as fs from 'fs';
import * as util from 'util';
import * as child_process from 'child_process';
import * as Git from 'nodegit';
import * as express from 'express';
import { c } from './lib/Log';
import { hbs } from './lib/Hbs';
import __rootDir, { __klausDir, __nodeDir } from './lib/RootDirFinder';
import { Utils } from './lib/Utils';
const __exec = util.promisify(child_process.exec);

const app = express();
const PORT = process.env.PORT || 8888;
const ROOT_REPOSITORIES = __rootDir+`/repositories`;


// Express setup
app.set('views', `${__nodeDir}/views`);
app.set('view engine', 'hbs');
app.engine('hbs', hbs.renderFile.bind(hbs));

app.use(
	'/static',
	express.static(`${__klausDir}/static`)
);


const _get_repo_and_rev = async (
	repoName: string,
	/**
	 * Branch/commit-sha/tag
	 */
	revId?: string,
	path?: string,
) => {
	if (path && revId) {
		revId += `/` + Utils.trimSuffix(path, '/');
	}
	let repo: Git.Repository;
	try {
		repo = await Git.Repository.openBare(`${ROOT_REPOSITORIES}/${repoName}.git`);
	} catch {
		throw new Error(`No such repository ${repoName}`);
	}
	if (!revId) {
		revId = `master`;
	}
	
	let commit: Git.Commit;
	try {
		commit = await repo.getCommit(revId);
	} catch {
		try {
			c.log(revId);
			commit = await repo.getBranchCommit(revId);
		} catch {
			throw new Error(`Invalid rev id`);
		}
	};
	return {
		repoName,
		repo,
		revId,
		path,
		commit,
	};
};


/**
 * Routes(html)
 */

app.get('/', async function(req, res) {
	const repoFolders = await fs.promises.readdir(ROOT_REPOSITORIES);
	/// ^^ For now, simply assume top-level folders in this dir
	/// are our repos.
	/// Also assume they are bare repos.
	const repos = await Promise.all(repoFolders.map(x => {
		return Git.Repository.openBare(`${ROOT_REPOSITORIES}/${x}`);
	}));
	const headCommits = await Promise.all(repos.map(x => x.getHeadCommit()));
	
	res.render('repo_list', {
		items: Utils.zip(repos, headCommits).map(x => ({ repo: x[0], commit: x[1] })),
		order_by: req.query['by-name'] ? 'name' : 'last_updated',
		meta: {
			title: `Repository list`,
		},
		layout: 'skeleton',
	});
});


app.get('/:repo', async function(req, res) {
	/// Show commits of a branch, just like `git log`
	const context = await _get_repo_and_rev(req.params.repo);
	const revWalk = context.repo.createRevWalk();
	revWalk.pushHead();
	const history = await revWalk.getCommits(50);
	
	res.render('index', {
		context,
		history,
		layout: 'base',
	});
});


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
	app.locals.SITE_NAME = process.env.KLAUS_SITE_NAME ?? "klaus-next";
	
	app.listen(PORT, () => {
		c.debug(`Running on http://localhost:${PORT}`);
	});
})();

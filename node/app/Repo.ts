import * as Git from 'nodegit';
import * as path from 'path';
import { c } from '../lib/Log';
import __rootDir from '../lib/RootDirFinder';
import { Utils } from '../lib/Utils';


/**
 * Helpers for our repos.
 */
export namespace Repo {
	export const ROOT_REPOS = __rootDir+`/repositories`;

	export function name(r: Git.Repository) {
		return Utils.trimSuffix(path.relative(ROOT_REPOS, r.path()), '.git');
	}
	
	export async function refs(r: Git.Repository): Promise<{
		tags: string[];
		branches: string[];
	}> {
		const tags = await Git.Tag.list(r);
		const branches = (await r.getReferences())
			.filter(x => x.isBranch())
			.map(x => x.shorthand())
		;
		return { tags, branches };
	}
	
	export async function numOfCommits(
		repo: Git.Repository,
		before: Git.Commit
	): Promise<number> {
		const revWalk = repo.createRevWalk();
		revWalk.push(before.id());
		let i = 1;
		/// ^^ Include `before` in the count.
		while (true) {
			try {
				await revWalk.next();
				i++;
			} catch(err) {
				if (err.errno === Git.Error.CODE.ITEROVER) {
					return i;
				}
				throw err;
			}
		}
	}
}

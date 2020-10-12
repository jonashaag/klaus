import type * as Git from 'nodegit';
import * as path from 'path';
import __rootDir from './RootDirFinder';
import { Utils } from './Utils';


/**
 * Helpers for our repos.
 */
export namespace Repo {
	export const ROOT_REPOS = __rootDir+`/repositories`;

	export function name(r: Git.Repository) {
		return Utils.trimSuffix(path.relative(ROOT_REPOS, r.path()), '.git');
	}
}

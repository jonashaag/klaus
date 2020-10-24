import * as util from 'util';
import * as child_process from 'child_process';
import { Context } from './Context';
import { Repo } from './Repo';
import { c } from '../lib/Log';
import { Utils } from '../lib/Utils';
const __exec = util.promisify(child_process.exec);

/**
 * Info not directly linked to the `context` itself
 * but that we want to display in the webpage.
 */
export namespace TemplateInfo {
	export async function info(
		context: Context,
		pageUrl: string,
	): Promise<{
		refs: Repo.Refs;
		/**
		 * We implement a "Check on GitHub" link that opens
		 * the "same" page on GitHub (for repos which have a remote there). 
		 * Peruse it to check that things work the same.
		 * 
		 * Might also work for other remotes...
		 */
		remoteLink?: string;
	}> {
		const refs = await Repo.refs(context.repo);
		try {
			let remoteUrl = (await __exec(
				`git config --get remote.origin.url`,
				{ cwd: context.repo.path() }
			)).stdout.trim();
			remoteUrl = Utils.trimSuffix(remoteUrl, `.git`);
			const relativeToRepo = Utils.trimPrefix(
				pageUrl,
				`/${context.repoName}`
			);
			const remoteLink = remoteUrl+relativeToRepo;
			c.debug(remoteLink);
			return { refs, remoteLink };
		} catch(err) {
			return { refs };
		}
	}
}

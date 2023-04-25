import * as fs from 'fs';
import * as path from 'path';

export type Scalar = string | number | boolean | undefined | null;

export namespace Utils {
	/**
	 * Returns s without the provided prefix, or s if doesn't start with prefix.
	 */
	export function trimPrefix(s: string, prefix: string): string {
		if (s.startsWith(prefix)) {
			return s.substr(prefix.length);
		}
		return s;
	}
	/**
	 * Returns s without the provided suffix, or s if doesn't end with suffix.
	 */
	export function trimSuffix(s: string, suffix: string): string {
		if (s.endsWith(suffix)) {
			return s.substr(0, s.length - suffix.length);
		}
		return s;
	}
	/**
	 * Recursive version that accepts an array of prefixes.
	 */
	export function trimPrefixes(s: string, prefixes: string[]): string {
		for (const x of prefixes) {
			if (s.startsWith(x)) {
				return trimPrefixes(s.substr(x.length), prefixes);
			}
		}
		return s;
	}
	/**
	 * Recursive version that accepts an array of suffixes.
	 */
	export function trimSuffixes(s: string, suffixes: string[]): string {
		for (const x of suffixes) {
			if (s.endsWith(x)) {
				return trimSuffixes(s.substr(0, s.length - x.length), suffixes);
			}
		}
		return s;
	}
	
	/**
	 * Number prettifier
	 * Transforms 123456789 to 123,456,789
	 */
	export function prettyNumber(n: number): string {
		const parts: string[] = [];
		while (n > 1000) {
			const remainer = n % 1000;
			parts.unshift(`${remainer}`.padStart(3, "0"));
			n -= remainer;
			n /= 1000;
		}
		
		let t = `${n}`;
		if (parts.length > 0) {
			t += `,${parts.join(',')}`;
		}
		return t;
	}
	
	/**
	 * Merge multiple containers into tuples.
	 */
	export function zip<U, V>(keys: U[], values: V[]): [U, V][] {
		return keys.map((k, i): [U, V] => [ k, values[i] ]);
	}
	
	/**
	 * One param:  create list of integers from 0 (inclusive) to n (exclusive)
	 * Two params: create list of integers from a (inclusive) to b (exclusive)
	 */
	export function range(n: number, b?: number): number[] {
		return (b)
			? Array(b - n).fill(0).map((_, i) => n + i)
			: Array(n).fill(0).map((_, i) => i);
	}
	
	/**
	 * Filter-out undefined values
	 */
	export function filterUndef<T>(arr: (T | undefined)[]): T[] {
		return arr.filter((x): x is T => x !== undefined);
	}
	
	/**
	 * Does local file exist.
	 */
	export async function fileExists(path: string): Promise<boolean> {
		try {
			await fs.promises.access(path);
			return true;
		} catch {
			return false;
		}
	}
	
	/**
	 * Recursive readdir matching fs.Dirent[]
	 * 
	 * Use `matchDirEnt` to select what's returned
	 */
	export async function readdirREnt(
		dirpath: string,
		matchDirEnt: (x: fs.Dirent) => boolean = () => true,
		maxDepth?: number,
	): Promise<string[]> {
		const dirEnts = await fs.promises.readdir(dirpath, {
			withFileTypes: true,
		});
		const children = dirEnts.filter(x => matchDirEnt(x))
			.map(x => path.join(dirpath, x.name))
		;
		if (maxDepth === undefined || maxDepth > 1) {
			const mD = !!maxDepth
				? maxDepth - 1
				: undefined
			;
			const descendants = (await Promise.all(
				dirEnts
					.filter(x => x.isDirectory())
					.map(x => readdirREnt(path.join(dirpath, x.name), matchDirEnt, mD))
			)).flat();
			
			return [
				...children,
				...descendants,
			];
		} else {
			return children;
		}
	}
}

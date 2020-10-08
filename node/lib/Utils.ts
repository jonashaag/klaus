import * as fs from 'fs';
import * as util from 'util';
import * as child_process from 'child_process';
const __exec = util.promisify(child_process.exec);

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
	 * Merge multiple containers into tuples.
	 */
	export function zip<U, V>(keys: U[], values: V[]): [U, V][] {
		return keys.map((k, i): [U, V] => [ k, values[i] ]);
	}
}

import { normalize } from 'path';

const rootDirFinder = function(): string {
	const parts = __dirname.split('/');
	let level = parts.length - 1;
	while (level > 0) {
		const currentPath = parts.slice(0, level).join('/');
		try {
			require(`${currentPath}/package.json`);
			return normalize(currentPath+`/..`);
		} catch (err) { }
		level --;
	}
	return "";
};
const __rootDir = rootDirFinder();
export const __klausDir = __rootDir+`/klaus`;
export const __nodeDir  = __rootDir+`/node`;

export default __rootDir;

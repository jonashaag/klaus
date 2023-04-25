import * as colors from 'colors';
import * as util from 'util';



export const c = {
	__log: (args: any[], opts: {
		color?: colors.Color,
		colors?: boolean,
	} = {}) => {
		const inspectOpts = (opts.colors !== undefined)
			? { depth: 20, colors: opts.colors }
			: { depth: 20, colors: true }
		;
		const s = args.map(o => {
			if (o instanceof Error) {
				return (o.stack || `${o.name}: ${o.message}`)
					.split('\n')
					.map(x => colors.red(x))
					.join('\n')
				;
			} else if (typeof o === 'string') {
				return o;
			} else {
				return util.inspect(o, inspectOpts);
			}
		}).join('  ');
		console.log(opts.color ? opts.color(s) : s);
	},
	log: (...args) => {
		c.__log(args);
	},
	debug: (...args) => {
		c.__log(args, { color: colors.gray, colors: false });
	},
	success: (...args) => {
		c.__log(args, { color: colors.green });
	},
	error: (...args) => {
		c.__log(args, { color: colors.red });
	},
	info: (...args) => {
		c.__log(args, { color: colors.cyan });
	},
	introspect: (...args) => {
		c.__log(args.map(a => [
			a,
			typeof a,
			a.constructor.name,
		]));
	},
}

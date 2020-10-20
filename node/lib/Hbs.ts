import type { Repository } from 'nodegit';
import { DateTime } from 'luxon';
import { __nodeDir } from './RootDirFinder';
import { HbsEngine } from './HbsEngine';
import { Repo } from '../app/Repo';
import { c } from './Log';

export const hbs = new HbsEngine();


/**
 * Block helpers or mixed-use helpers
 * (can be used as block helpers or in sub-expressions)
 * 
 * see stackoverflow.com/a/31632215/593036
 */

hbs.handlebars.registerHelper('eq', function(arg1, arg2, options: Partial<Handlebars.HelperOptions>) {
	const x = arg1 === arg2;
	if (options.fn) {
		return x ? options.fn(this) : options.inverse?.(this);
	}
	return x;
});

hbs.handlebars.registerHelper('not', function(arg1, arg2, options: Partial<Handlebars.HelperOptions>) {
	const x = arg1 !== arg2;
	if (options.fn) {
		return x ? options.fn(this) : options.inverse?.(this);
	}
	return x;
});

hbs.handlebars.registerHelper('or', function(...args) {
	const options: Partial<Handlebars.HelperOptions> = args[args.length - 1];
	const xArgs = args.slice(0, -1);
	const x = xArgs.some(Boolean);
	if (options.fn) {
		return x ? options.fn(this) : options.inverse?.(this);
	}
	return x;
});

hbs.handlebars.registerHelper('and', function(...args) {
	const options: Partial<Handlebars.HelperOptions> = args[args.length - 1];
	const xArgs = args.slice(0, -1);
	const x = xArgs.every(Boolean);
	if (options.fn) {
		return x ? options.fn(this) : options.inverse?.(this);
	}
	return x;
});

hbs.handlebars.registerHelper('instanceof', function(arg1, arg2: string, options: Handlebars.HelperOptions) {
	return (arg1.constructor.name === arg2) ? options.fn(this) : options.inverse(this);
});

hbs.handlebars.registerHelper('startsWith', function(
	s: string,
	prefix: string,
	options: Handlebars.HelperOptions
) {
	return (s.startsWith(prefix)) ? options.fn(this) : options.inverse(this);
});

hbs.handlebars.registerHelper('ifIn', function(
	s: string,
	list: string | string[] | undefined,
	options: Handlebars.HelperOptions
) {
	if (!list) {
		return options.inverse(this);
	}
	
	const arr = Array.isArray(list) ? list : list.split(",").map(x => x.trim());
	return (arr.includes(s)) ? options.fn(this) : options.inverse(this);
});


/**
 * "Simple" helpers
 */

hbs.handlebars.registerHelper('urlenc', (str) => {
	return encodeURIComponent(str);
});

hbs.handlebars.registerHelper('stringify', (o) => {
	if (o === undefined) {
		return `undefined`;
	}
	return JSON.stringify(o);
});

hbs.handlebars.registerHelper('timestamp', (o: Date) => {
	return Math.floor(o.getTime() / 1_000);
});

hbs.handlebars.registerHelper('dateUTC', (o: Date) => {
	/// `Fri, 07 Feb 2020 17:12:40 GMT`
	return o.toUTCString();
});

hbs.handlebars.registerHelper('dateISO', (o: Date) => {
	/// `2020-02-07T17:12:40`
	return o.toISOString().slice(0, 19);
});

hbs.handlebars.registerHelper('dateString', (x: number) => {
	/// `10/19/2020`
	/// input is milliseconds since epoch.
	const date = new Date(x);
	return date.toLocaleDateString('en-US');
});

hbs.handlebars.registerHelper('fromNow', (o: Date) => {
	const dt = DateTime.fromJSDate(o);
	return dt.toRelative();
});

hbs.handlebars.registerHelper('firstLine', (s: string) => {
	return s.split('\n')[0];
});

hbs.handlebars.registerHelper('typeof', (o: any) => {
	return typeof o;
});

hbs.handlebars.registerHelper('call', function(o: any, method: string, ...args: any[]) {
	// The hbs binding/scoping is kinda insane
	// so `call o.method` wouldn't work.
	args.pop();
	return o[method](...args);
});


/**
 * App-specific
 */
hbs.handlebars.registerHelper('repo_name', (r: Repository) => {
	return Repo.name(r);
});

hbs.handlebars.registerHelper('shorten_sha1', (rev: string) => {
	if (typeof rev !== 'string') {
		rev = (<any>rev).toString();
	}
	if (/^[A-F0-9]+$/i.test(rev) && rev.length >= 20) {
		return rev.substr(0, 7);
	}
	return rev;
});

hbs.registerPartials(__nodeDir+`/views/partials`);

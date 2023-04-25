import * as fs from 'fs';
import * as path from 'path';
import * as chokidar from 'chokidar';
import * as Handlebars from 'handlebars';
import { config, Environment } from './config';
import { c } from './Log';



export class HbsEngine {
	handlebars = Handlebars.create();
	
	private async readAllPartials(dir: string) {
		const filenames = await fs.promises.readdir(dir);
		for (const fname of filenames) {
			const name = path.basename(fname, path.extname(fname));
			const x = await fs.promises.readFile(path.join(dir, fname), 'utf8');
			this.handlebars.registerPartial(name, x);
		}
	}
	
	/**
	 * @param dir Path to the partials directory.
	 */
	registerPartials(dir: string) {
		this.readAllPartials(dir);
		if (config.environment === Environment.development) {
			chokidar.watch(dir, {
				ignoreInitial: true,
			}).on('all', () => {
				c.debug(`[hbs] partials.change`);
				this.readAllPartials(dir);
			});
		}
	}
	
	/**
	 * Express middleware.
	 * 
	 * @param filepath is absolute.
	 * @param options Contains data, plus res.locals and app.locals.
	 */
	async renderFile(
		filepath: string,
		options: Record<string, any>,
		__callback: (err: any, rendered: string) => void,
	) {
		/// Note: `options` also contains res.locals and app.locals.
		
		const runtimeOpts: Handlebars.RuntimeOptions = {
			allowProtoPropertiesByDefault: true,
			allowProtoMethodsByDefault: true,
		};
		/// ^^ handlebarsjs.com/api-reference/runtime-options.html
		
		const str = await fs.promises.readFile(filepath, 'utf8');
		const template = this.handlebars.compile(str);
		const output = template(options, runtimeOpts);
		
		if (options.layout === false) {
			__callback(undefined, output);
		} else {
			/// Has layout.
			let filenameL = typeof options.layout === 'string'
				? options.layout
				: `layout.hbs`
			;
			if (!filenameL.endsWith(`.hbs`)) {
				filenameL += ".hbs";
			}
			const pathLayout = path.join(options.settings.views, filenameL);
			const strLayout = await fs.promises.readFile(pathLayout, 'utf8');
			const templateL = this.handlebars.compile(strLayout);
			options.body = output;
			__callback(undefined, templateL(options, runtimeOpts));
		}
	}
}



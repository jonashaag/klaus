

type EnvironmentType = "development" | "production" | "staging";
export class Environment {
	static development: EnvironmentType = "development";
	static production:  EnvironmentType = "production";
	static staging:     EnvironmentType = "staging";
	
	static current(): EnvironmentType {
		switch (process.env.NODE_ENV) {
			case Environment.development:
				return Environment.development;
			case Environment.production:
				return Environment.production;
			case Environment.staging:
				return Environment.staging;
			default:
				return Environment.development;
		}
	}
}


export const config = {
	environment: Environment.current(),
}

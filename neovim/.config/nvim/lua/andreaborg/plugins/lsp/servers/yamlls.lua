local kubernetes_schema =
	"https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v1.32.1-standalone-strict/all.json"

return {
	settings = {
		yaml = {
			schemaStore = {
				enable = false,
				url = "",
			},
			schemas = require("schemastore").yaml.schemas({
				extra = {
					{
						description = "Kubernetes 1.36.1",
						fileMatch = {
							-- exact k8s/ at root (both direct and nested)
							"k8s/*.yaml",
							"k8s/*.yml",
							"k8s/**/*.yaml",
							"k8s/**/*.yml",
							"kubernetes/*.yaml",
							"kubernetes/*.yml",
							"kubernetes/**/*.yaml",
							"kubernetes/**/*.yml",
							-- any dir containing k8s in name (e.g. k8s-dats/production/deployment.yaml)
							"*k8s*/*.yaml",
							"*k8s*/*.yml",
							"*k8s*/**/*.yaml",
							"*k8s*/**/*.yml",
							"**/*k8s*/*.yaml",
							"**/*k8s*/*.yml",
							"**/*k8s*/**/*.yaml",
							"**/*k8s*/**/*.yml",
							-- explicit k8s suffix files anywhere
							"*.k8s.yaml",
							"*.k8s.yml",
							"**/*.k8s.yaml",
							"**/*.k8s.yml",
						},
						name = "kubernetes-1.36.1",
						url = kubernetes_schema,
					},
				},
			}),
			format = {
				enable = true,
			},
			validate = true,
		},
	},
}

local kubernetes_schema =
	"https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v1.36.1-standalone-strict/all.json"

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
							"k8s/**/*.yaml",
							"k8s/**/*.yml",
							"kubernetes/**/*.yaml",
							"kubernetes/**/*.yml",
							"*.k8s.yaml",
							"*.k8s.yml",
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

local schemas = require("schemastore").yaml.schemas()

-- Scope Kubernetes validation to manifest paths; other YAML keeps its SchemaStore schema.
schemas.kubernetes = {
	"**/k8s*/**/*.yaml",
	"**/k8s*/**/*.yml",
	"**/kubernetes/**/*.yaml",
	"**/kubernetes/**/*.yml",
	"**/*.k8s.yaml",
	"**/*.k8s.yml",
}

vim.lsp.config("yamlls", {
	-- lspconfig's default filetypes include yaml.docker-compose, which is owned solely by
	-- docker_language_server here, so keep the narrower local filetypes.
	filetypes = { "yaml", "yaml.gitlab", "yaml.helm-values" },
	settings = {
		yaml = {
			kubernetesVersion = "1.36.1",
			kubernetesCRDStore = { enable = true },
			schemaStore = { enable = false, url = "" },
			schemas = schemas,
			validate = true,
		},
	},
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
	end,
})

vim.lsp.enable("yamlls")

local format = require("languages.lsp.format")

format.format_on_save({ "yaml", "yaml.gitlab", "yaml.helm-values" }, format.format_yaml)

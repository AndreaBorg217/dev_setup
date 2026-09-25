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
	cmd = { "yaml-language-server", "--stdio" },
	filetypes = { "yaml", "yaml.gitlab", "yaml.helm-values" },
	root_markers = { ".git" },
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

local function format_yaml(bufnr)
	local before = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
	local input = table.concat(before, "\n") .. "\n"
	local after = vim.fn.systemlist({ "yamlfmt", "-in" }, input)
	if vim.v.shell_error ~= 0 then
		vim.notify("yamlfmt could not format this YAML file", vim.log.levels.ERROR)
		return
	end

	-- Preserve diagnostic positions on lines the formatter leaves alone.
	local hunks = vim.diff(input, table.concat(after, "\n") .. "\n", { result_type = "indices" })
	for index = #hunks, 1, -1 do
		local hunk = hunks[index]
		local start = hunk[1] - (hunk[2] > 0 and 1 or 0)
		local replacement = {}
		for line = hunk[3], hunk[3] + hunk[4] - 1 do
			table.insert(replacement, after[line])
		end
		vim.api.nvim_buf_set_lines(bufnr, start, start + hunk[2], false, replacement)
	end
end

vim.api.nvim_create_autocmd("FileType", {
	group = vim.api.nvim_create_augroup("yaml_format", { clear = true }),
	pattern = { "yaml", "yaml.gitlab", "yaml.helm-values" },
	callback = function(args)
		vim.keymap.set("n", "<leader>fmt", function()
			format_yaml(args.buf)
		end, { buffer = args.buf, desc = "Format YAML file" })
		vim.api.nvim_create_autocmd("BufWritePre", {
			group = vim.api.nvim_create_augroup("yaml_format_" .. args.buf, { clear = true }),
			buffer = args.buf,
			callback = function()
				if require("config").AUTO_FORMAT then
					format_yaml(args.buf)
				end
			end,
		})
	end,
})

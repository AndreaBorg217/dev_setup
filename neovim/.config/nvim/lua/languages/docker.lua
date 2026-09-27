-- Compose files need their own filetype so Docker's server receives the dockercompose language ID.
vim.filetype.add({
	filename = {
		["docker-compose.yml"] = "yaml.docker-compose",
		["docker-compose.yaml"] = "yaml.docker-compose",
		["compose.yml"] = "yaml.docker-compose",
		["compose.yaml"] = "yaml.docker-compose",
	},
})

local format = require("languages.lsp.format")

local function format_dockerfile(bufnr)
	local before = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
	local input = table.concat(before, "\n") .. "\n"
	local after = vim.fn.systemlist({ "dockerfmt", "--newline" }, input)
	if vim.v.shell_error ~= 0 then
		vim.notify("dockerfmt could not format this file", vim.log.levels.ERROR)
		return
	end
	format.apply_diff(bufnr, after)
end

format.format_on_save({ "dockerfile", "yaml.docker-compose" }, function(bufnr)
	if vim.bo[bufnr].filetype == "dockerfile" then
		format_dockerfile(bufnr)
	else
		format.format_yaml(bufnr)
	end
end)

vim.lsp.config("docker_language_server", {
	-- lspconfig's cmd/filetypes/root_markers/get_language_id default is equivalent here:
	-- it's a superset covering hcl.docker-bake, a filetype this project never registers.
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
	end,
})

vim.lsp.enable("docker_language_server")

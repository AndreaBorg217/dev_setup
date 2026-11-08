local function format_go(bufnr, client)
	if vim.bo[bufnr].filetype == "go" then
		local params = vim.lsp.util.make_range_params(0, client.offset_encoding)
		params.context = { only = { "source.organizeImports" }, diagnostics = {} }
		local response = client:request_sync("textDocument/codeAction", params, 5000, bufnr)
		if not response or response.error then
			vim.notify("gopls could not organise Go imports", vim.log.levels.ERROR)
			return
		end
		for _, action in ipairs(response.result or {}) do
			if action.edit then
				vim.lsp.util.apply_workspace_edit(action.edit, client.offset_encoding)
			end
		end
	end
	vim.lsp.buf.format({ bufnr = bufnr, id = client.id, timeout_ms = 5000 })
end

-- lspconfig's cmd/filetypes default is identical here; its root_dir function is a superset
-- (falls back to the same go.work/go.mod/.git markers, plus GOROOT/GOMODCACHE handling).
vim.lsp.config("gopls", {
	settings = {
		gopls = {
			analyses = { unusedparams = true, shadow = true },
			staticcheck = true,
			gofumpt = true,
			hints = {
				assignVariableTypes = true,
				compositeLiteralFields = true,
				compositeLiteralTypes = true,
				constantValues = true,
				functionTypeParameters = true,
				parameterNames = true,
				rangeVariableTypes = true,
			},
		},
	},
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
		vim.keymap.set("n", "<leader>fmt", function()
			format_go(bufnr, client)
		end, { buffer = bufnr, desc = "Format Go file and organise imports" })
		vim.api.nvim_create_autocmd("BufWritePre", {
			group = vim.api.nvim_create_augroup("go_format_" .. bufnr, { clear = true }),
			buffer = bufnr,
			callback = function()
				if require("config").AUTO_FORMAT then
					format_go(bufnr, client)
				end
			end,
		})
	end,
})

vim.lsp.enable("gopls")

-- Run golangci-lint as a second server for checks beyond gopls; overlapping warnings may appear twice.
-- lspconfig's cmd default is identical; its filetypes/root_markers are supersets (also
-- gomod/go.work/.golangci.toml/.golangci.json), which is harmless here, so they're dropped too.
vim.lsp.config("golangci_lint_ls", {
	init_options = {
		command = { "golangci-lint", "run", "--output.json.path", "stdout", "--show-stats=false", "--issues-exit-code=1" },
	},
})

vim.lsp.enable("golangci_lint_ls")

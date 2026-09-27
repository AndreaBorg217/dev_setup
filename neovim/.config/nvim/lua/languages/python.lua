local function apply_ruff_action(client, bufnr, kind)
	local params = vim.lsp.util.make_range_params(0, client.offset_encoding)
	params.context = { only = { kind }, diagnostics = {} }
	local response = client:request_sync("textDocument/codeAction", params, 5000, bufnr)
	if not response or response.error then
		vim.notify("Ruff could not apply " .. kind, vim.log.levels.ERROR)
		return
	end
	for _, action in ipairs(response.result or {}) do
		local resolved = client:request_sync("codeAction/resolve", action, 5000, bufnr)
		if resolved and resolved.result and resolved.result.edit then
			vim.lsp.util.apply_workspace_edit(resolved.result.edit, client.offset_encoding)
		end
	end
end

local function format_python(bufnr, client)
	apply_ruff_action(client, bufnr, "source.fixAll.ruff")
	apply_ruff_action(client, bufnr, "source.organizeImports.ruff")
	vim.lsp.buf.format({ bufnr = bufnr, id = client.id, timeout_ms = 5000 })
end

vim.lsp.config("ty", {
	-- lspconfig's cmd/filetypes default is identical; root_markers is kept because this
	-- project also treats uv.lock as a root, which lspconfig's default list lacks.
	root_markers = { "ty.toml", "pyproject.toml", "uv.lock", "setup.py", "setup.cfg", "requirements.txt", ".git" },
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
	end,
})

vim.lsp.enable("ty")

-- Ruff owns lint, fixes, imports and formatting; ty owns type intelligence and hover.
-- lspconfig's cmd/filetypes/root_markers default is identical here.
vim.lsp.config("ruff", {
	init_options = {
		settings = {
			lineLength = 120,
			lint = { select = { "ALL" }, ignore = { "CPY001" }, preview = true },
		},
	},
	on_attach = function(client, bufnr)
		client.server_capabilities.hoverProvider = false
		vim.keymap.set("n", "<leader>fmt", function()
			format_python(bufnr, client)
		end, { buffer = bufnr, desc = "Fix and format Python file" })
		vim.api.nvim_create_autocmd("BufWritePre", {
			group = vim.api.nvim_create_augroup("python_format_" .. bufnr, { clear = true }),
			buffer = bufnr,
			callback = function()
				if require("config").AUTO_FORMAT then
					format_python(bufnr, client)
				end
			end,
		})
	end,
})

vim.lsp.enable("ruff")

local dap = require("dap")
dap.adapters.python = { type = "executable", command = "debugpy-adapter" }
dap.configurations.python = {
	{
		type = "python",
		request = "launch",
		name = "Launch current file",
		program = "${file}",
		-- Use the active shell's Python instead of Mason's private debugpy environment.
		pythonPath = function()
			return vim.fn.exepath("python3")
		end,
	},
}

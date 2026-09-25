-- Location mappings jump to one result or show a Telescope picker for several.
vim.api.nvim_create_autocmd("LspAttach", {
	group = vim.api.nvim_create_augroup("lsp_keymaps", { clear = true }),
	callback = function(event)
		local builtin = require("telescope.builtin")
		local buffer = event.buf
		local client = vim.lsp.get_client_by_id(event.data.client_id)
		if client:supports_method("textDocument/codeLens") then
			vim.lsp.codelens.enable(true, { bufnr = buffer })
		end
		vim.keymap.set("n", "gR", builtin.lsp_references, { buffer = buffer, desc = "Find references" })
		vim.keymap.set("n", "<leader>gr", builtin.lsp_references, { buffer = buffer, desc = "Find references" })
		vim.keymap.set("n", "gd", builtin.lsp_definitions, { buffer = buffer, desc = "Find definitions" })
		vim.keymap.set("n", "<leader>gd", builtin.lsp_definitions, { buffer = buffer, desc = "Find definitions" })
		vim.keymap.set("n", "gi", builtin.lsp_implementations, { buffer = buffer, desc = "Find implementations" })
		vim.keymap.set("n", "<leader>gi", builtin.lsp_implementations, { buffer = buffer, desc = "Find implementations" })
		vim.keymap.set("n", "gt", builtin.lsp_type_definitions, { buffer = buffer, desc = "Find type definitions" })
		vim.keymap.set("n", "<leader>gt", builtin.lsp_type_definitions, { buffer = buffer, desc = "Find type definitions" })
		vim.keymap.set("n", "<leader>gs", builtin.lsp_document_symbols, { buffer = buffer, desc = "Find document symbols" })
		vim.keymap.set({ "n", "v" }, "<leader>ca", vim.lsp.buf.code_action, { buffer = buffer, desc = "Code actions" })
		vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, { buffer = buffer, desc = "Rename symbol" })
		vim.keymap.set("n", "K", vim.lsp.buf.hover, { buffer = buffer, desc = "Show hover documentation" })
		vim.keymap.set("n", "<leader>oi", function()
			vim.lsp.buf.code_action({
				apply = true,
				context = { only = { "source.organizeImports" }, diagnostics = {} },
			})
		end, { buffer = buffer, desc = "Organise imports" })
	end,
})

vim.keymap.set("n", "]e", function()
	vim.diagnostic.jump({ count = 1, severity = vim.diagnostic.severity.ERROR })
end, { desc = "Next error" })
vim.keymap.set("n", "[e", function()
	vim.diagnostic.jump({ count = -1, severity = vim.diagnostic.severity.ERROR })
end, { desc = "Previous error" })

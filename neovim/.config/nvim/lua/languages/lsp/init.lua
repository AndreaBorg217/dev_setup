local file_operations = require("languages.lsp.file_operations")

-- Debounce edits sent to servers and extend capabilities with file-operations support.
vim.lsp.config("*", {
	flags = { debounce_text_changes = 50 },
	capabilities = file_operations.capabilities,
})

-- winborder is already set globally (options.lua), so no explicit border here.
vim.api.nvim_create_autocmd("LspAttach", {
	group = vim.api.nvim_create_augroup("lsp_inlay_hints", { clear = true }),
	callback = function(event)
		local client = vim.lsp.get_client_by_id(event.data.client_id)
		if client and client.server_capabilities.inlayHintProvider then
			vim.lsp.inlay_hint.enable(true, { bufnr = event.buf })
		end
	end,
})

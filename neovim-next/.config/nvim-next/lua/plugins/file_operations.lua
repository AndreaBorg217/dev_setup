-- nvim-tree emits file events, but Neovim does not forward them to LSP servers.
vim.pack.add({ "https://github.com/antosha417/nvim-lsp-file-operations" }, { confirm = false })

local file_operations = require("lsp-file-operations")
file_operations.setup()

vim.lsp.config("*", {
	capabilities = vim.tbl_deep_extend(
		"force",
		vim.lsp.protocol.make_client_capabilities(),
		file_operations.default_capabilities()
	),
})

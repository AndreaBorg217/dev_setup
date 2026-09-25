vim.diagnostic.config({
	virtual_text = true, -- Show diagnostic messages beside the affected code.
	update_in_insert = true, -- Keep diagnostic displays current while typing.
	severity_sort = true, -- Show the most severe diagnostic first on each line.
	signs = {
		text = {
			[vim.diagnostic.severity.ERROR] = " ",
			[vim.diagnostic.severity.WARN] = " ",
			[vim.diagnostic.severity.HINT] = "󰠠 ",
			[vim.diagnostic.severity.INFO] = " ",
		},
	},
	float = { border = "rounded", source = "always", header = "", prefix = "" },
	jump = {
		on_jump = function(_, bufnr)
			vim.diagnostic.open_float({ bufnr = bufnr, scope = "cursor", focus = false })
		end,
	},
})

vim.lsp.config("*", { flags = { debounce_text_changes = 50 } }) -- Send edits to language servers promptly.

require("languages.keymaps")
require("languages.python")
require("languages.java")
require("languages.go")
require("languages.docker")
require("languages.json")
require("languages.yaml")
require("languages.bash")
require("languages.lua")
require("languages.markdown")

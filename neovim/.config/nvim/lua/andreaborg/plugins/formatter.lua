return {
	"stevearc/conform.nvim",
	event = { "BufReadPre", "BufNewFile" },
	config = function()
		local conform = require("conform")
		conform.setup({
			formatters_by_ft = {
				python = { "ruff_fix", "ruff_organize_imports", "ruff_format" },
				go = { "goimports", "gofumpt" },
				yaml = { "yamlfmt" },
				lua = { "stylua" },
				markdown = { "prettier" },
				json = { "prettier" },
				java = { "palantir_java_format" },
			},
			formatters = {
				palantir_java_format = {
					command = "palantir-java-format",
					args = { "--palantir", "--assume-filename", "$FILENAME", "-" },
					stdin = true,
					exit_codes = { 0 },
				},
			},
			format_on_save = {
				lsp_fallback = true,
				async = false,
				timeout_ms = 5000,
			},
		})
		vim.keymap.set({ "n" }, "<leader>fmt", function()
			conform.format({
				lsp_fallback = true,
				async = false,
				timeout_ms = 5000,
			})
		end, { desc = "Format file" })
	end,
}

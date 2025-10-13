return {
	"stevearc/conform.nvim",
	event = { "BufReadPre", "BufNewFile" },
	config = function()
		local conform = require("conform")

		conform.setup({
			formatters_by_ft = {
				-- Python formatting
				python = { "black" },

				-- Go formatting
				go = { "goimports", "gofumpt" },

				-- YAML formatting
				yaml = { "yamlfmt" },

				-- Lua formatting (for Neovim config)
				lua = { "stylua" },

				-- Markdown formatting
				markdown = { "prettier" },

				-- JSON formatting
				json = { "prettier" },
			},
			format_on_save = {
				lsp_fallback = true,
				async = false,
				timeout_ms = 3000,
			},
		})

		vim.keymap.set({ "n" }, "<leader>ff", function()
			conform.format({
				lsp_fallback = true,
				async = false,
				timeout_ms = 1000,
			})
		end, { desc = "Format file" })
	end,
}

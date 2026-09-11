return {
	"mfussenegger/nvim-lint",
	event = { "BufReadPre", "BufNewFile" },
	config = function()
		local lint = require("lint")

		lint.linters_by_ft = {
			python = { "ruff", "cspell" },
			java = { "cspell" },
			go = { "golangcilint", "cspell" },
			dockerfile = { "hadolint", "cspell" },
			yaml = { "yamllint", "cspell" },
			markdown = { "cspell" },
		}

		table.insert(lint.linters.ruff.args, #lint.linters.ruff.args, "--extend-select")
		table.insert(lint.linters.ruff.args, #lint.linters.ruff.args, "AIR")

		local function try_linting()
			lint.try_lint()
		end

		local lint_augroup = vim.api.nvim_create_augroup("lint", { clear = true })
		vim.api.nvim_create_autocmd({ "BufEnter", "BufWritePost", "InsertLeave" }, {
			group = lint_augroup,
			callback = function()
				try_linting()
			end,
		})

		vim.keymap.set("n", "<leader>lf", function()
			try_linting()
		end, { desc = "Trigger linting for current file" })
	end,
}

return {
	"mfussenegger/nvim-lint",
	event = { "BufReadPre", "BufNewFile" },
	config = function()
		local lint = require("lint")

		lint.linters_by_ft = {
			-- ruff as LSP already provides diagnostics + code actions (fixAll/organizeImports)
			-- keeping it here duplicates every ruff diagnostic (LSP `Ruff (F841)` + nvim-lint `ruff`)
			-- see https://github.com/astral-sh/ruff/issues/17594 - use one or the other
			python = {},
			java = {},
			go = { "golangcilint" },
			dockerfile = { "hadolint" },
			yaml = { "yamllint" },
			markdown = { "cspell" },
		}

		-- yamllint: disable noisy k8s-irrelevant rules
		-- comments = "too few spaces before comment" | document-start = "missing ---"
		lint.linters.yamllint.args = {
			"--format",
			"parsable",
			"-d",
			"{extends: default, rules: {comments: {min-spaces-from-content: -1}, document-start: disable}}",
			"-",
		}

		local function try_linting()
			lint.try_lint()
		end

		local lint_augroup = vim.api.nvim_create_augroup("lint", { clear = true })
		vim.api.nvim_create_autocmd({ "BufEnter", "BufWritePost", "InsertLeave", "TextChanged", "TextChangedI" }, {
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

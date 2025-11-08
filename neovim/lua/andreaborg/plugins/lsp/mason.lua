return {
	"williamboman/mason.nvim",
	dependencies = {
		"williamboman/mason-lspconfig.nvim",
		"WhoIsSethDaniel/mason-tool-installer.nvim",
	},
	config = function()
		-- import mason
		local mason = require("mason")
		-- import mason-lspconfig
		local mason_lspconfig = require("mason-lspconfig")
		local mason_tool_installer = require("mason-tool-installer")
		-- enable mason and configure icons
		mason.setup({
			ui = {
				icons = {
					package_installed = "✓",
					package_pending = "➜",
					package_uninstalled = "✗",
				},
			},
		})
		mason_lspconfig.setup({
			-- list of servers for mason to install
			ensure_installed = {
				"pyright", -- Python LSP
				"gopls", -- Go LSP
				"lua_ls", -- Lua LSP (for Neovim config)
				"yamlls", -- YAML LSP
				"dockerls", -- Dockerfile LSP
				"docker_compose_language_service", -- Docker Compose LSP
				"ts_ls", -- TypeScript LSP
				"eslint",
				"cssls", -- CSS LSP
			},
		})
		mason_tool_installer.setup({
			ensure_installed = {
				-- Python tools
				"black", -- Python formatter
				"isort", -- Python import sorter
				"pylint", -- Python linter
				"mypy", -- Python type checker

				-- Go tools
				"gofumpt", -- Go formatter (stricter than gofmt)
				"goimports", -- Go import formatter
				"golangci-lint", -- Go linter
				"gomodifytags", -- Go struct tag modifier
				"impl", -- Go interface implementation generator

				-- YAML tools
				"yamllint", -- YAML linter
				"yamlfmt", -- YAML formatter

				-- Docker tools
				"hadolint", -- Dockerfile linter

				-- Lua to tools
				"stylua", -- Lua formatter

				-- React
				"eslint_d",
				"prettier",
			},
		})
	end,
}

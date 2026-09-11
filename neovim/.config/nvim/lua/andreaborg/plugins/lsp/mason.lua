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
			ensure_installed = {
				"pyright",
				"gopls",
				"jdtls",
				"lua_ls",
				"yamlls",
				"dockerls",
				"docker_compose_language_service",
			},
			automatic_enable = {
				"pyright",
				"gopls",
				"jdtls",
				"lua_ls",
				"yamlls",
				"dockerls",
				"docker_compose_language_service",
			},
		})
		mason_tool_installer.setup({
			ensure_installed = {
				"ruff",
				"gofumpt",
				"goimports",
				"golangci-lint",
				"gomodifytags",
				"impl",
				"yamllint",
				"yamlfmt",
				"hadolint",
				"cspell",
				"stylua",
				"prettier",
				"java-debug-adapter",
				{ "java-test", version = "0.46.0" },
				"palantir-java-format",
				"vscode-spring-boot-tools",
			},
		})
	end,
}

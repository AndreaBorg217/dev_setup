-- Mason installs language-tool binaries; native vim.lsp still configures each server.
vim.pack.add({
	"https://github.com/mason-org/mason.nvim",
	"https://github.com/WhoIsSethDaniel/mason-tool-installer.nvim",
}, { confirm = false })

require("mason").setup()
local tools = {
	{ "lua-language-server", version = "3.19.1" },
	{ "json-lsp", version = "4.10.0" },
	{ "bash-language-server", version = "5.8.1" },
	{ "shellcheck", version = "v0.11.0" },
	{ "shfmt", version = "v3.14.1" },
	{ "marksman", version = "2026-02-08" },
	{ "prettier", version = "3.9.8" },
	{ "docker-language-server", version = "v0.20.1" },
	{ "dockerfmt", version = "v0.5.4" },
	{ "yamlfmt", version = "v0.21.0" },
	{ "yaml-language-server", version = "1.24.0" },
	{ "gopls", version = "v0.23.0" },
	{ "golangci-lint", version = "v2.12.2" },
	{ "golangci-lint-langserver", version = "v0.0.12" },
	{ "ty", version = "0.0.75" },
	{ "ruff", version = "0.16.8" },
	{ "debugpy", version = "1.8.22" },
	{ "jdtls", version = "v1.61.0" },
	{ "java-debug-adapter", version = "0.59.0" },
	{ "palantir-java-format", version = "2.99.0" },
	{ "vscode-spring-boot-tools", version = "2.2.0" },
}
require("mason-tool-installer").setup({
	ensure_installed = tools,
	auto_update = false,
})

return tools

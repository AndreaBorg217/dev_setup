-- Smoke test: confirms nvim-next launches headless with its config loaded
-- and the mason-installed tool binaries used by the suites are on PATH.
local script_dir = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":h")
local common = dofile(script_dir .. "/common.lua")

local required_tools = {
	"jdtls",
	"palantir-java-format",
	"ty",
	"ruff",
	"debugpy-adapter",
	"gopls",
	"golangci-lint-langserver",
	"dlv",
	"bash-language-server",
	"docker-language-server",
	"vscode-json-language-server",
	"lua-language-server",
	"marksman",
	"prettier",
	"yaml-language-server",
	"yamlfmt",
}

for _, tool in ipairs(required_tools) do
	if vim.fn.executable(tool) == 1 then
		common.record("smoke:" .. tool, "PASS", "on PATH")
	else
		common.record("smoke:" .. tool, "FAIL", "not on PATH")
	end
end

common.record("smoke:config-loaded", vim.fn.exists(":NvimTreeToggle") == 2 and "PASS" or "FAIL", "nvim-tree command registered")

common.report_and_quit()

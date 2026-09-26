-- Go (gopls + golangci_lint_ls) test-matrix rows, run headless against nvim-next.
local script_dir = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":h")
local common = dofile(script_dir .. "/common.lua")

local lab_root = os.getenv("LAB_ROOT") or (os.getenv("HOME") .. "/tmp/nvim-next-lab")
local project = lab_root .. "/go"
vim.cmd("cd " .. vim.fn.fnameescape(project))

local function call_leader_fmt(bufnr)
	local map = vim.fn.maparg("<leader>fmt", "n", false, true)
	if not map or not map.callback then
		return false, "no <leader>fmt mapping for this buffer"
	end
	vim.api.nvim_buf_call(bufnr, map.callback)
	return true
end

local main_buf = vim.fn.bufadd(project .. "/main.go")
vim.fn.bufload(main_buf)
vim.api.nvim_set_current_buf(main_buf)
vim.cmd("doautocmd FileType go")

-- 1. gopls and golangci_lint_ls attach ----------------------------------------

local gopls_client = common.wait_for_client(main_buf, "gopls", 30000)
local lint_client = common.wait_for_client(main_buf, "golangci_lint_ls", 30000)
if gopls_client and lint_client then
	common.record("go-gopls-golangci-attach", "PASS", "both clients attached")
else
	common.record("go-gopls-golangci-attach", "FAIL", "gopls=" .. tostring(gopls_client ~= nil) .. " golangci_lint_ls=" .. tostring(lint_client ~= nil))
end

-- 2. Diagnostics (planted staticcheck issue) ----------------------------------

-- golangci-lint runs asynchronously as an external process on top of gopls;
-- give it up to 60s beyond first-diagnostic to surface its own findings
-- (source names are the underlying linter/check, e.g. "ineffassign", "SA4006").
common.wait_until(60000, function()
	local ds = vim.diagnostic.get(main_buf)
	for _, d in ipairs(ds) do
		if d.source == "ineffassign" or (d.source and d.source:match("^SA%d")) then
			return true
		end
	end
	return false
end)
local diags = vim.diagnostic.get(main_buf)
local has_staticcheck_diag = false
for _, d in ipairs(diags) do
	if d.source == "ineffassign" or (d.source and d.source:match("^SA%d")) then
		has_staticcheck_diag = true
	end
end
common.record("go-diagnostics", has_staticcheck_diag and "PASS" or "FAIL", #diags .. " diagnostic(s), golangci-lint/staticcheck finding found=" .. tostring(has_staticcheck_diag))

-- 3. gofumpt-style format (via gopls settings.gofumpt=true) -------------------

local before_lines = vim.api.nvim_buf_get_lines(main_buf, 0, -1, false)
local ok, err = call_leader_fmt(main_buf)
if ok then
	vim.wait(3000)
	local after_lines = vim.api.nvim_buf_get_lines(main_buf, 0, -1, false)
	local changed = not vim.deep_equal(before_lines, after_lines)
	common.record("go-gofumpt-format", "PASS", "format invoked via gopls (settings.gofumpt=true), buffer_changed=" .. tostring(changed))
else
	common.record("go-gofumpt-format", "FAIL", err)
end

-- 4. Code actions --------------------------------------------------------------

local current_diags = vim.diagnostic.get(main_buf)
local params = vim.lsp.util.make_range_params(0, gopls_client and gopls_client.offset_encoding or "utf-16")
params.context = {
	diagnostics = vim.tbl_map(function(d)
		return d.user_data.lsp
	end, current_diags),
}
local response = vim.lsp.buf_request_sync(main_buf, "textDocument/codeAction", params, 10000)
local found_action = false
if response then
	for _, res in pairs(response) do
		if res.result and #res.result > 0 then
			found_action = true
		end
	end
end
common.record("go-code-actions", found_action and "PASS" or "FAIL", "code actions returned")

-- 5. documentLink (import paths) -----------------------------------------------

local link_response = vim.lsp.buf_request_sync(main_buf, "textDocument/documentLink", {
	textDocument = { uri = vim.uri_from_bufnr(main_buf) },
}, 10000)
local has_links = false
if link_response then
	for _, res in pairs(link_response) do
		if res.result and #res.result > 0 then
			has_links = true
		end
	end
end
common.record("go-document-link", has_links and "PASS" or "FAIL", "documentLink for import paths")

-- 6. Inlay hints -------------------------------------------------------------------

vim.lsp.inlay_hint.enable(true, { bufnr = main_buf })
vim.wait(2000)
local hints = vim.lsp.inlay_hint.get({ bufnr = main_buf })
common.record("go-inlay-hints", #hints > 0 and "PASS" or "FAIL", #hints .. " hint(s) observed")

-- 7. Rename ---------------------------------------------------------------------

local lines = vim.api.nvim_buf_get_lines(main_buf, 0, -1, false)
local rename_line_idx, rename_col
for i, line in ipairs(lines) do
	local col = line:find("func add")
	if col then
		rename_line_idx = i - 1
		rename_col = col + 4
		break
	end
end
local rename_response = vim.lsp.buf_request_sync(main_buf, "textDocument/rename", {
	textDocument = { uri = vim.uri_from_bufnr(main_buf) },
	position = { line = rename_line_idx, character = rename_col },
	newName = "sum",
}, 10000)
local rename_touches_test = false
if rename_response then
	for _, res in pairs(rename_response) do
		if res.result and res.result.changes then
			for uri, _ in pairs(res.result.changes) do
				if uri:find("main_test") then
					rename_touches_test = true
				end
			end
		end
		if res.result and res.result.documentChanges then
			for _, change in ipairs(res.result.documentChanges) do
				if change.textDocument and change.textDocument.uri:find("main_test") then
					rename_touches_test = true
				end
			end
		end
	end
end
common.record("go-rename", rename_touches_test and "PASS" or "FAIL", "rename touches main_test.go: " .. tostring(rename_touches_test))

-- 8. DAP debug main (hand-written dlv adapter at baseline) -----------------------

local dap = require("dap")
local lines_now = vim.api.nvim_buf_get_lines(main_buf, 0, -1, false)
local bp_line
for i, line in ipairs(lines_now) do
	if line:find('fmt.Println') then
		bp_line = i
		break
	end
end
vim.api.nvim_win_set_cursor(0, { bp_line, 0 })
dap.set_breakpoint()

local stopped = false
dap.listeners.after.event_stopped["go_test"] = function()
	stopped = true
end
dap.run(dap.configurations.go[1])
common.wait_until(30000, function()
	return stopped
end)
dap.listeners.after.event_stopped["go_test"] = nil
pcall(function()
	dap.terminate()
end)
common.record("go-dap-debug-main", stopped and "PASS" or "FAIL", "breakpoint hit via hand-written dlv adapter")

-- 9. DAP "Debug test" pick with cursor in main_test.go (dap-go, after-state) --------

local test_buf = vim.fn.bufadd(project .. "/main_test.go")
vim.fn.bufload(test_buf)
vim.api.nvim_set_current_buf(test_buf)
vim.cmd("doautocmd FileType go")
local test_lines = vim.api.nvim_buf_get_lines(test_buf, 0, -1, false)
local cursor_line, bp_test_line
for i, line in ipairs(test_lines) do
	if line:find("func TestAdd") then
		cursor_line = i
	end
	-- add(2, 3) == 5, so t.Fatal's branch never runs; break on the always-executed
	-- condition line instead.
	if line:find("if add") then
		bp_test_line = i
	end
end
vim.api.nvim_win_set_cursor(0, { bp_test_line, 0 })
dap.set_breakpoint()
vim.api.nvim_win_set_cursor(0, { cursor_line, 0 })

-- dap-go (leoluz/nvim-dap-go, wired via plugins/dap.lua's require('dap-go').setup())
-- finds the nearest test under the cursor via treesitter and launches it under delve.
local test_stopped = false
dap.listeners.after.event_stopped["go_test_debug_test"] = function()
	test_stopped = true
end
require("dap-go").debug_test()
common.wait_until(30000, function()
	return test_stopped
end)
dap.listeners.after.event_stopped["go_test_debug_test"] = nil
pcall(function()
	dap.terminate()
end)
common.record("go-dap-debug-test", test_stopped and "PASS" or "FAIL", "dap-go debug_test() stopped at breakpoint in TestAdd: " .. tostring(test_stopped))

common.report_and_quit()

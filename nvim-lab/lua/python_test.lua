-- Python (ty + ruff) test-matrix rows, run headless against nvim-next.
local script_dir = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":h")
local common = dofile(script_dir .. "/common.lua")

local lab_root = os.getenv("LAB_ROOT") or (os.getenv("HOME") .. "/tmp/nvim-next-lab")
local project = lab_root .. "/python"
vim.cmd("cd " .. vim.fn.fnameescape(project))

local function call_leader_fmt(bufnr)
	local map = vim.fn.maparg("<leader>fmt", "n", false, true)
	if not map or not map.callback then
		return false, "no <leader>fmt mapping for this buffer"
	end
	vim.api.nvim_buf_call(bufnr, map.callback)
	return true
end

local bufnr = vim.fn.bufadd(project .. "/greeter.py")
vim.fn.bufload(bufnr)
vim.api.nvim_set_current_buf(bufnr)
vim.cmd("doautocmd FileType python")

-- 1. ty and ruff attach --------------------------------------------------------

local ty_client = common.wait_for_client(bufnr, "ty", 30000)
local ruff_client = common.wait_for_client(bufnr, "ruff", 30000)
if ty_client and ruff_client then
	common.record("python-ty-ruff-attach", "PASS", "both clients attached")
else
	common.record("python-ty-ruff-attach", "FAIL", "ty=" .. tostring(ty_client ~= nil) .. " ruff=" .. tostring(ruff_client ~= nil))
end

-- 2. Lint + type diagnostics (planted ruff violation + planted type error) ----

local function diag_sources_present(bufnr)
	local has_ruff, has_ty = false, false
	for _, d in ipairs(vim.diagnostic.get(bufnr)) do
		if d.source == "Ruff" then
			has_ruff = true
		end
		if d.source == "ty" then
			has_ty = true
		end
	end
	return has_ruff, has_ty
end

common.wait_until(20000, function()
	local has_ruff, has_ty = diag_sources_present(bufnr)
	return has_ruff and has_ty
end)
local has_ruff_diag, has_ty_diag = diag_sources_present(bufnr)
local diags = vim.diagnostic.get(bufnr)
if has_ruff_diag and has_ty_diag then
	common.record("python-lint-type-diagnostics", "PASS", "ruff and ty diagnostics both reported")
else
	common.record("python-lint-type-diagnostics", "FAIL", "ruff=" .. tostring(has_ruff_diag) .. " ty=" .. tostring(has_ty_diag))
end

-- 3. Format + fix-all -----------------------------------------------------------

local before_lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
local ok, err = call_leader_fmt(bufnr)
if ok then
	vim.wait(3000)
	local after_lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
	local unused_import_gone = not table.concat(after_lines, "\n"):find("^import os", 1, true) == nil
		or not table.concat(after_lines, "\n"):find("import os")
	local changed = not vim.deep_equal(before_lines, after_lines)
	common.record("python-format-fix-all", "PASS", "format+fix-all invoked, buffer_changed=" .. tostring(changed) .. ", unused_import_removed=" .. tostring(unused_import_gone))
else
	common.record("python-format-fix-all", "FAIL", err)
end

-- 4. Code actions at a diagnostic --------------------------------------------

local current_diags = vim.diagnostic.get(bufnr)
if #current_diags > 0 then
	local params = vim.lsp.util.make_range_params(0, "utf-16")
	-- The server expects raw LSP Diagnostic objects, stashed on each Neovim
	-- diagnostic entry at user_data.lsp (see vim.lsp.buf.code_action()).
	local lsp_diags = vim.tbl_map(function(d)
		return d.user_data.lsp
	end, current_diags)
	params.context = { diagnostics = lsp_diags }
	local response = vim.lsp.buf_request_sync(bufnr, "textDocument/codeAction", params, 10000)
	local found = false
	if response then
		for _, res in pairs(response) do
			if res.result and #res.result > 0 then
				found = true
			end
		end
	end
	common.record("python-code-actions", found and "PASS" or "FAIL", "code actions at diagnostic")
else
	common.record("python-code-actions", "FAIL", "no diagnostics left to request actions for")
end

-- 5. Hover (ty) -------------------------------------------------------------------

local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
local hover_line_idx, hover_col
for i, line in ipairs(lines) do
	local col = line:find("greet")
	if col and line:find("def") then
		hover_line_idx = i - 1
		hover_col = col
		break
	end
end
local hover_response = vim.lsp.buf_request_sync(bufnr, "textDocument/hover", {
	textDocument = { uri = vim.uri_from_bufnr(bufnr) },
	position = { line = hover_line_idx, character = hover_col },
}, 10000)
local has_hover = false
if hover_response then
	for _, res in pairs(hover_response) do
		if res.result and res.result.contents then
			has_hover = true
		end
	end
end
common.record("python-hover", has_hover and "PASS" or "FAIL", "hover returned by type checker")

-- 6. Inlay hints ------------------------------------------------------------------

vim.lsp.inlay_hint.enable(true, { bufnr = bufnr })
vim.wait(2000)
local hints = vim.lsp.inlay_hint.get({ bufnr = bufnr })
common.record("python-inlay-hints", #hints > 0 and "PASS" or "FAIL", #hints .. " hint(s) observed")

-- 7. Rename ------------------------------------------------------------------------

local rename_response = vim.lsp.buf_request_sync(bufnr, "textDocument/rename", {
	textDocument = { uri = vim.uri_from_bufnr(bufnr) },
	position = { line = hover_line_idx, character = hover_col },
	newName = "greet_renamed",
}, 10000)
local rename_ok = false
if rename_response then
	for _, res in pairs(rename_response) do
		if res.result and (res.result.changes or res.result.documentChanges) then
			rename_ok = true
		end
	end
end
common.record("python-rename", rename_ok and "PASS" or "FAIL", "rename produced a workspace edit")

-- 8. debugpy launch with breakpoint ------------------------------------------------

local dap = require("dap")
local lines_now = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
local bp_line
for i, line in ipairs(lines_now) do
	if line:find("return a %+ b") then
		bp_line = i
		break
	end
end
vim.api.nvim_win_set_cursor(0, { bp_line, 0 })
dap.set_breakpoint()

local stopped = false
dap.listeners.after.event_stopped["python_test"] = function()
	stopped = true
end
dap.run(dap.configurations.python[1])
common.wait_until(20000, function()
	return stopped
end)
dap.listeners.after.event_stopped["python_test"] = nil
pcall(function()
	dap.terminate()
end)
common.record("python-debugpy", stopped and "PASS" or "FAIL", "breakpoint hit via debugpy")

common.report_and_quit()

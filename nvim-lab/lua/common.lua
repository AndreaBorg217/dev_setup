-- Shared helpers for the headless lab test scripts.
-- Loaded with `dofile` by each suite script; not a plugin module.

local M = {}

M.results = {}

function M.record(row, status, note)
	table.insert(M.results, { row = row, status = status, note = note or "" })
end

function M.report_and_quit()
	for _, entry in ipairs(M.results) do
		print(string.format("RESULT\t%s\t%s\t%s", entry.row, entry.status, entry.note))
	end
	vim.cmd("qa!")
end

-- Polls `check` every 100ms until it returns a truthy value or `timeout_ms` elapses.
function M.wait_until(timeout_ms, check)
	local ok = vim.wait(timeout_ms, check, 100)
	return ok
end

-- Waits for at least one LSP client matching `name` to attach to `bufnr`.
function M.wait_for_client(bufnr, name, timeout_ms)
	local client
	M.wait_until(timeout_ms or 30000, function()
		local clients = vim.lsp.get_clients({ bufnr = bufnr, name = name })
		if #clients > 0 then
			client = clients[1]
			return true
		end
		return false
	end)
	return client
end

-- Waits for at least one diagnostic to be reported for `bufnr`.
function M.wait_for_diagnostics(bufnr, timeout_ms)
	local diagnostics
	M.wait_until(timeout_ms or 30000, function()
		diagnostics = vim.diagnostic.get(bufnr)
		return #diagnostics > 0
	end)
	return diagnostics or {}
end

return M

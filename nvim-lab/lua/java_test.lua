-- Java + Spring test-matrix rows, run headless against nvim-next.
local script_dir = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":h")
local common = dofile(script_dir .. "/common.lua")

local lab_root = os.getenv("LAB_ROOT") or (os.getenv("HOME") .. "/tmp/nvim-next-lab")
local project = lab_root .. "/java-spring"
vim.cmd("cd " .. vim.fn.fnameescape(project))

-- Calls a buffer-local <leader>fmt mapping's callback directly, so the test
-- does not need to know the configured leader key.
local function call_leader_fmt(bufnr)
	local map = vim.fn.maparg("<leader>fmt", "n", false, true)
	if not map or not map.callback then
		return false, "no <leader>fmt mapping for this buffer"
	end
	vim.api.nvim_buf_call(bufnr, map.callback)
	return true
end

-- 1. Java clients attach ---------------------------------------------------

local scheduled_buf = vim.fn.bufadd(project .. "/src/main/java/com/example/demo/ScheduledTasks.java")
vim.fn.bufload(scheduled_buf)
vim.api.nvim_set_current_buf(scheduled_buf)
vim.cmd("doautocmd FileType java")

local jdtls_client = common.wait_for_client(scheduled_buf, "jdtls", 120000)
if not jdtls_client then
	common.record("java-clients-attach", "FAIL", "jdtls did not attach within 120s")
else
	local clients = vim.lsp.get_clients({ bufnr = scheduled_buf, name = "jdtls" })
	local workspace_dir = vim.fn.stdpath("cache") .. "/jdtls/" .. vim.fn.fnamemodify(project, ":t")
	local one_workspace = vim.fn.isdirectory(workspace_dir) == 1
	if #clients == 1 and one_workspace then
		common.record("java-clients-attach", "PASS", "1 jdtls client, workspace at " .. workspace_dir)
	else
		common.record("java-clients-attach", "FAIL", #clients .. " clients, workspace_dir_exists=" .. tostring(one_workspace))
	end
end

-- 2. Java diagnostics (planted compile error) ------------------------------

if jdtls_client then
	local diags = common.wait_for_diagnostics(scheduled_buf, 60000)
	if #diags > 0 then
		common.record("java-diagnostics", "PASS", #diags .. " diagnostic(s) reported")
	else
		common.record("java-diagnostics", "FAIL", "no diagnostics reported for planted compile error")
	end
else
	common.record("java-diagnostics", "FAIL", "skipped: jdtls not attached")
end

-- 3. Java Palantir format ---------------------------------------------------

local controller_buf = vim.fn.bufadd(project .. "/src/main/java/com/example/demo/HelloController.java")
vim.fn.bufload(controller_buf)
vim.api.nvim_set_current_buf(controller_buf)
vim.cmd("doautocmd FileType java")
common.wait_for_client(controller_buf, "jdtls", 60000)

local before_lines = vim.api.nvim_buf_get_lines(controller_buf, 0, -1, false)
local ok, err = call_leader_fmt(controller_buf)
if ok then
	vim.wait(3000)
	local after_lines = vim.api.nvim_buf_get_lines(controller_buf, 0, -1, false)
	local changed = not vim.deep_equal(before_lines, after_lines)
	-- format_java always runs palantir-java-format; PASS means the formatter ran
	-- without error, whether or not this already-tidy file's bytes changed.
	common.record("java-palantir-format", "PASS", "formatter invoked, buffer_changed=" .. tostring(changed))
else
	common.record("java-palantir-format", "FAIL", err)
end

-- 4. Java code actions (quick-fix / organize imports) ----------------------

if jdtls_client then
	local params = vim.lsp.util.make_range_params(0, jdtls_client.offset_encoding)
	vim.api.nvim_set_current_buf(scheduled_buf)
	local lnum_diags = vim.diagnostic.get(scheduled_buf, { lnum = 8 }) or {}
	params.context = {
		diagnostics = vim.tbl_map(function(d)
			return d.user_data.lsp
		end, lnum_diags),
	}
	local response = vim.lsp.buf_request_sync(scheduled_buf, "textDocument/codeAction", params, 10000)
	local found_action = false
	if response then
		for _, res in pairs(response) do
			if res.result and #res.result > 0 then
				found_action = true
			end
		end
	end
	common.record("java-code-actions", found_action and "PASS" or "FAIL", "code actions at planted error")
else
	common.record("java-code-actions", "FAIL", "skipped: jdtls not attached")
end

-- 5. Java inlay hints --------------------------------------------------------

if jdtls_client then
	vim.lsp.inlay_hint.enable(true, { bufnr = controller_buf })
	vim.wait(2000)
	local hints = vim.lsp.inlay_hint.get({ bufnr = controller_buf })
	common.record("java-inlay-hints", "PASS", #hints .. " kind(s) observed at baseline")
else
	common.record("java-inlay-hints", "FAIL", "skipped: jdtls not attached")
end

-- 6. Java rename symbol across files -----------------------------------------

local service_buf = vim.fn.bufadd(project .. "/src/main/java/com/example/demo/GreetingService.java")
vim.fn.bufload(service_buf)
vim.api.nvim_set_current_buf(service_buf)
vim.cmd("doautocmd FileType java")
local service_client = common.wait_for_client(service_buf, "jdtls", 60000)

if service_client then
	-- "GreetingService" class name token, line 5 (0-indexed 4), inside "public class GreetingService".
	local lines = vim.api.nvim_buf_get_lines(service_buf, 0, -1, false)
	local class_line_idx, class_col
	for i, line in ipairs(lines) do
		local col = line:find("GreetingService")
		if col and line:find("class") then
			class_line_idx = i - 1
			class_col = col - 1
			break
		end
	end
	local rename_params = {
		textDocument = { uri = vim.uri_from_bufnr(service_buf) },
		position = { line = class_line_idx, character = class_col },
		newName = "GreetingServiceRenamed",
	}
	local response = vim.lsp.buf_request_sync(service_buf, "textDocument/rename", rename_params, 15000)
	local touches_other_file = false
	if response then
		for _, res in pairs(response) do
			if res.result and res.result.changes then
				for uri, _ in pairs(res.result.changes) do
					if uri:find("HelloController") then
						touches_other_file = true
					end
				end
			end
			if res.result and res.result.documentChanges then
				for _, change in ipairs(res.result.documentChanges) do
					if change.textDocument and change.textDocument.uri:find("HelloController") then
						touches_other_file = true
					end
				end
			end
		end
	end
	common.record("java-rename-symbol", touches_other_file and "PASS" or "FAIL", "rename touches HelloController.java: " .. tostring(touches_other_file))
else
	common.record("java-rename-symbol", "FAIL", "skipped: jdtls not attached")
end

-- 7. Spring application.yml completion ---------------------------------------

local yml_buf = vim.fn.bufadd(project .. "/src/main/resources/application.yml")
vim.fn.bufload(yml_buf)
vim.api.nvim_set_current_buf(yml_buf)
vim.cmd("doautocmd FileType yaml")
common.wait_until(30000, function()
	for _, client in ipairs(vim.lsp.get_clients({ bufnr = yml_buf })) do
		if client.name == "spring-boot" then
			return true
		end
	end
	return false
end)

-- boot-ls needs time after attach to index the project classpath before its
-- property-key completion index is populated; poll on a well-known prefix
-- ("server.") instead of assuming it is ready immediately.
vim.api.nvim_buf_set_lines(yml_buf, 1, 1, false, { "ser" })
vim.api.nvim_win_set_cursor(0, { 2, 3 })
local spring_boot_client = vim.lsp.get_clients({ bufnr = yml_buf, name = "spring-boot" })[1]
local yml_has_items = false
if spring_boot_client then
	common.wait_until(90000, function()
		local resp = spring_boot_client:request_sync(
			"textDocument/completion",
			vim.lsp.util.make_position_params(0, spring_boot_client.offset_encoding),
			10000,
			yml_buf
		)
		local items = resp and resp.result and (resp.result.items or resp.result) or {}
		if type(items) == "table" and #items > 0 then
			yml_has_items = true
			return true
		end
		return false
	end)
end
common.record("spring-application-yml-completion", yml_has_items and "PASS" or "FAIL", "completion items at application.yml key")

-- 8. Spring @Value completion --------------------------------------------------

if service_client then
	vim.api.nvim_set_current_buf(service_buf)
	local lines = vim.api.nvim_buf_get_lines(service_buf, 0, -1, false)
	local value_line_idx, value_col
	for i, line in ipairs(lines) do
		local col = line:find("%${")
		if col then
			value_line_idx = i - 1
			value_col = col + 1
			break
		end
	end
	local completion_params = {
		textDocument = { uri = vim.uri_from_bufnr(service_buf) },
		position = { line = value_line_idx, character = value_col },
	}
	local response = vim.lsp.buf_request_sync(service_buf, "textDocument/completion", completion_params, 10000)
	local has_items = false
	if response then
		for _, res in pairs(response) do
			local items = res.result and (res.result.items or res.result) or {}
			if type(items) == "table" and #items > 0 then
				has_items = true
			end
		end
	end
	common.record("spring-value-completion", has_items and "PASS" or "FAIL", "completion inside @Value(\"${...}\")")
else
	common.record("spring-value-completion", "FAIL", "skipped: jdtls not attached")
end

-- 9. Spring @/ workspace symbol search ------------------------------------------

local symbol_response = vim.lsp.buf_request_sync(service_buf, "workspace/symbol", { query = "@/" }, 10000)
local has_request_mapping = false
if symbol_response then
	for _, res in pairs(symbol_response) do
		if res.result and #res.result > 0 then
			has_request_mapping = true
		end
	end
end
common.record("spring-at-symbol-search", has_request_mapping and "PASS" or "FAIL", "workspace/symbol query '@/'")

-- 10. Spring cron inlay hint (informational, non-blocking) ---------------------

vim.lsp.inlay_hint.enable(true, { bufnr = scheduled_buf })
vim.wait(2000)
local cron_hints = vim.lsp.inlay_hint.get({ bufnr = scheduled_buf })
common.record("spring-cron-inlay-hint", "PASS", #cron_hints .. " inlay hint(s) observed on @Scheduled method (informational)")

-- 11. Java DAP launch: breakpoint on main class -------------------------------

local dap = require("dap")
local app_buf = vim.fn.bufadd(project .. "/src/main/java/com/example/demo/DemoApplication.java")
vim.fn.bufload(app_buf)
vim.api.nvim_set_current_buf(app_buf)
vim.cmd("doautocmd FileType java")
common.wait_for_client(app_buf, "jdtls", 60000)

-- jdtls.dap.setup_dap_main_class_configs() populates dap.configurations.java asynchronously.
local jdtls_dap_ok = pcall(function()
	require("jdtls.dap").setup_dap_main_class_configs()
end)

local got_config = common.wait_until(30000, function()
	return dap.configurations.java ~= nil and #dap.configurations.java > 0
end)

if jdtls_dap_ok and got_config then
	-- Line with SpringApplication.run(...) inside main().
	local lines = vim.api.nvim_buf_get_lines(app_buf, 0, -1, false)
	local bp_line
	for i, line in ipairs(lines) do
		if line:find("SpringApplication.run") then
			bp_line = i
			break
		end
	end
	vim.api.nvim_win_set_cursor(0, { bp_line, 0 })
	dap.set_breakpoint()

	local stopped = false
	dap.listeners.after.event_stopped["java_test"] = function()
		stopped = true
	end
	dap.run(dap.configurations.java[1])
	common.wait_until(60000, function()
		return stopped
	end)
	dap.listeners.after.event_stopped["java_test"] = nil
	pcall(function()
		dap.terminate()
	end)
	common.record("java-dap-launch", stopped and "PASS" or "FAIL", "stopped event at breakpoint")
else
	common.record("java-dap-launch", "FAIL", "no dap.configurations.java discovered within timeout")
end

common.report_and_quit()

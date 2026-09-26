-- Misc language sample suite: LSP attach + <leader>fmt baseline capture,
-- one row each for bash, docker, json, lua, markdown, yaml.
local script_dir = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":h")
local common = dofile(script_dir .. "/common.lua")

local lab_root = os.getenv("LAB_ROOT") or (os.getenv("HOME") .. "/tmp/nvim-next-lab")
local project = lab_root .. "/misc"
local phase = os.getenv("LAB_PHASE") or "baseline"
vim.cmd("cd " .. vim.fn.fnameescape(project))

local snapshot_dir = project .. "/formatted-" .. phase
vim.fn.mkdir(snapshot_dir, "p")

local function call_leader_fmt(bufnr)
	local map = vim.fn.maparg("<leader>fmt", "n", false, true)
	if not map or not map.callback then
		return false, "no <leader>fmt mapping for this buffer"
	end
	vim.api.nvim_buf_call(bufnr, map.callback)
	return true
end

local samples = {
	{ name = "bash", file = "sample.sh", filetype = "sh" },
	{ name = "docker", file = "Dockerfile", filetype = "dockerfile" },
	{ name = "json", file = "sample.json", filetype = "json" },
	{ name = "lua", file = "sample.lua", filetype = "lua" },
	{ name = "markdown", file = "sample.md", filetype = "markdown" },
	{ name = "yaml", file = "sample.yaml", filetype = "yaml" },
}

for _, sample in ipairs(samples) do
	local bufnr = vim.fn.bufadd(project .. "/" .. sample.file)
	vim.fn.bufload(bufnr)
	vim.api.nvim_set_current_buf(bufnr)
	vim.cmd("doautocmd FileType " .. sample.filetype)

	local attached = common.wait_until(20000, function()
		return #vim.lsp.get_clients({ bufnr = bufnr }) > 0
	end)
	common.record("misc-attach-" .. sample.name, attached and "PASS" or "FAIL", "server attach for " .. sample.file)

	local ok, err = call_leader_fmt(bufnr)
	if ok then
		vim.wait(2000)
		local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
		local snapshot_path = snapshot_dir .. "/" .. sample.file
		vim.fn.writefile(lines, snapshot_path)
		common.record("misc-format-" .. sample.name, "PASS", "baseline copy written to " .. snapshot_path)
	else
		common.record("misc-format-" .. sample.name, "FAIL", err)
	end
end

common.report_and_quit()

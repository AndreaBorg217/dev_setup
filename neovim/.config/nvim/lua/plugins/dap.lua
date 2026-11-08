-- Neovim's LSP client cannot set breakpoints or step through programs.
vim.pack.add({ "https://codeberg.org/mfussenegger/nvim-dap" }, { confirm = false })
-- Go debug configurations and Delve setup for nvim-dap.
vim.pack.add({ "https://github.com/leoluz/nvim-dap-go" }, { confirm = false })

local dap = require("dap")
require("dap-go").setup()
vim.fn.sign_define("DapBreakpoint", { text = "", texthl = "DiagnosticSignError" })
local mapped_arrows = {}

local function restore_arrows()
	for _, key in ipairs(mapped_arrows) do
		vim.keymap.del("n", key)
	end
	mapped_arrows = {}
end

vim.keymap.set("n", "<leader>b", dap.toggle_breakpoint, { desc = "Toggle breakpoint" })
vim.keymap.set("n", "<leader>dc", dap.continue, { desc = "Start or continue debugging" })
vim.keymap.set("n", "<leader>dq", function()
	dap.terminate()
	restore_arrows()
end, { desc = "Stop debugging" })

-- Keep cursor movement on the arrows outside an active debug session.
dap.listeners.after.event_initialized["debug_arrows"] = function()
	vim.keymap.set("n", "<Left>", dap.step_out, { desc = "Step out" })
	vim.keymap.set("n", "<Down>", dap.step_over, { desc = "Step over" })
	vim.keymap.set("n", "<Right>", dap.step_into, { desc = "Step into" })
	mapped_arrows = { "<Left>", "<Down>", "<Right>" }
	if dap.session().capabilities.supportsRestartFrame then
		vim.keymap.set("n", "<Up>", dap.restart_frame, { desc = "Restart frame" })
		table.insert(mapped_arrows, "<Up>")
	end
end
dap.listeners.after.event_terminated["debug_arrows"] = restore_arrows
dap.listeners.after.event_exited["debug_arrows"] = restore_arrows

vim.pack.add({
	{ src = "https://github.com/igorlfs/nvim-dap-view", version = vim.version.range("1.*") },
}, { confirm = false })

local dap_view = require("dap-view")
dap_view.setup({
	auto_toggle = true,
	winbar = {
		sections = { "scopes", "watches", "exceptions", "breakpoints", "threads", "repl", "console" },
		default_section = "scopes",
	},
	virtual_text = {
		enabled = true,
		position = "inline",
	},
})

vim.keymap.set("n", "<leader>du", dap_view.toggle, { desc = "Toggle debugger view" })

local function focus_view(view)
	return function()
		dap_view.jump_to_view(view)
	end
end

vim.keymap.set("n", "<leader>ds", focus_view("scopes"), { desc = "Focus debugger scopes" })
vim.keymap.set("n", "<leader>dw", focus_view("watches"), { desc = "Focus debugger watches" })
vim.keymap.set("n", "<leader>de", focus_view("exceptions"), { desc = "Focus debugger exceptions" })
vim.keymap.set("n", "<leader>db", focus_view("breakpoints"), { desc = "Focus debugger breakpoints" })
vim.keymap.set("n", "<leader>dt", focus_view("threads"), { desc = "Focus debugger threads" })
vim.keymap.set("n", "<leader>dr", focus_view("repl"), { desc = "Focus debugger REPL" })
vim.keymap.set("n", "<leader>dC", focus_view("console"), { desc = "Focus debugger console" })

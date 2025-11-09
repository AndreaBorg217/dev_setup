return {
	{
		"mfussenegger/nvim-dap",
		dependencies = {
			"nvim-neotest/nvim-nio",
			"rcarriga/nvim-dap-ui",
			"mfussenegger/nvim-dap-python",
			"leoluz/nvim-dap-go",
			"theHamsta/nvim-dap-virtual-text",
		},
		config = function()
			local dap = require("dap")
			local dapui = require("dapui")
			-- pip install debugpy
			local dap_python = require("dap-python")
			-- go install github.com/go-delve/delve/cmd/dlv@latest
			-- export PATH=$PATH:$(go env GOPATH)/bin
			local dap_go = require("dap-go")

			require("dapui").setup({})
			require("nvim-dap-virtual-text").setup({
				commented = true, -- Show virtual text alongside comment
			})

			-- Setup Python
			-- dap_python.setup("python3")
			dap_python.setup("python")
			-- Setup Go
			dap_go.setup()

			vim.fn.sign_define("DapBreakpoint", {
				text = "",
				texthl = "DiagnosticSignError",
				linehl = "",
				numhl = "",
			})

			vim.fn.sign_define("DapBreakpointRejected", {
				text = "", -- or "❌"
				texthl = "DiagnosticSignError",
				linehl = "",
				numhl = "",
			})

			vim.fn.sign_define("DapStopped", {
				text = "", -- or "→"
				texthl = "DiagnosticSignWarn",
				linehl = "Visual",
				numhl = "DiagnosticSignWarn",
			})

			-- Store the code window when debugging starts
			local code_window = nil

			-- Automatically open/close DAP UI
			dap.listeners.after.event_initialized["dapui_config"] = function()
				-- Store current window (code window) before opening UI
				code_window = vim.api.nvim_get_current_win()
				dapui.open()
			end

			local opts = { noremap = true, silent = true }

			--	-- Toggle breakpoint
			vim.keymap.set("n", "<leader>db", function()
				dap.toggle_breakpoint()
			end, vim.tbl_extend("force", opts, { desc = "Toggle breakpoint" }))

			-- Continue / Start
			vim.keymap.set("n", "<leader>dc", function()
				dap.continue()
			end, vim.tbl_extend("force", opts, { desc = "Continue/Start debugging" }))

			-- Step Over
			vim.keymap.set("n", "<leader>do", function()
				dap.step_over()
			end, vim.tbl_extend("force", opts, { desc = "Step over" }))

			-- Step Into
			vim.keymap.set("n", "<leader>di", function()
				dap.step_into()
			end, vim.tbl_extend("force", opts, { desc = "Step into" }))

			-- Step Out
			vim.keymap.set("n", "<leader>dO", function()
				dap.step_out()
			end, vim.tbl_extend("force", opts, { desc = "Step out" }))

			-- Terminate debugging
			vim.keymap.set("n", "<leader>dq", function()
				require("dap").terminate()
				dapui.close()
			end, vim.tbl_extend("force", opts, { desc = "Terminate debugging" }))

			-- Toggle DAP UI
			vim.keymap.set("n", "<leader>du", function()
				dapui.toggle()
			end, vim.tbl_extend("force", opts, { desc = "Toggle DAP UI" }))

			-- Go-specific: Debug test (current test)
			vim.keymap.set("n", "<leader>dt", function()
				dap_go.debug_test()
			end, vim.tbl_extend("force", opts, { desc = "Debug Go test (current)" }))

			-- Go-specific: Debug last test
			vim.keymap.set("n", "<leader>dl", function()
				dap_go.debug_last_test()
			end, vim.tbl_extend("force", opts, { desc = "Debug Go test (last)" }))
			-- Helper function to find DAP UI window by buffer name pattern
			local function find_dapui_window(pattern)
				for _, win in ipairs(vim.api.nvim_list_wins()) do
					local buf = vim.api.nvim_win_get_buf(win)
					local buf_name = vim.api.nvim_buf_get_name(buf)
					if buf_name:match(pattern) then
						return win
					end
				end
				return nil
			end

			-- Switch to code window (leader + 0)
			vim.keymap.set("n", "<leader>0", function()
				if code_window and vim.api.nvim_win_is_valid(code_window) then
					vim.api.nvim_set_current_win(code_window)
				else
					print("Code window not found")
				end
			end, vim.tbl_extend("force", opts, { desc = "Focus code window" }))

			-- Switch to scopes window (leader + 1)
			vim.keymap.set("n", "<leader>d1", function()
				local win = find_dapui_window("DAP Scopes")
				if win then
					vim.api.nvim_set_current_win(win)
				else
					print("Scopes window not found")
				end
			end, vim.tbl_extend("force", opts, { desc = "Focus scopes window" }))

			-- Switch to breakpoints window (leader + 2)
			vim.keymap.set("n", "<leader>d2", function()
				local win = find_dapui_window("DAP Breakpoints")
				if win then
					vim.api.nvim_set_current_win(win)
				else
					print("Breakpoints window not found")
				end
			end, vim.tbl_extend("force", opts, { desc = "Focus breakpoints window" }))

			-- Switch to stacks window (leader + 3)
			vim.keymap.set("n", "<leader>d3", function()
				local win = find_dapui_window("DAP Stacks")
				if win then
					vim.api.nvim_set_current_win(win)
				else
					print("Stacks window not found")
				end
			end, vim.tbl_extend("force", opts, { desc = "Focus stacks window" }))

			-- Switch to watches window (leader + 4)
			vim.keymap.set("n", "<leader>d4", function()
				local win = find_dapui_window("DAP Watches")
				if win then
					vim.api.nvim_set_current_win(win)
				else
					print("Watches window not found")
				end
			end, vim.tbl_extend("force", opts, { desc = "Focus watches window" }))

			-- Switch to REPL window (leader + 5)
			vim.keymap.set("n", "<leader>d5", function()
				local win = find_dapui_window("dap%-repl")
				if win then
					vim.api.nvim_set_current_win(win)
				else
					print("REPL window not found")
				end
			end, vim.tbl_extend("force", opts, { desc = "Focus REPL window" }))

			-- Switch to console window (leader + 6)
			vim.keymap.set("n", "<leader>d6", function()
				local win = find_dapui_window("dap%-terminal")
				if win then
					vim.api.nvim_set_current_win(win)
				else
					print("Terminal window not found")
				end
			end, vim.tbl_extend("force", opts, { desc = "Focus terminal window" }))
		end,
	},
}

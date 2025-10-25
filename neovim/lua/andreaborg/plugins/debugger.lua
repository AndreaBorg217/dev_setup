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
			-- Automatically open/close DAP UI
			dap.listeners.after.event_initialized["dapui_config"] = function()
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
		end,
	},
}

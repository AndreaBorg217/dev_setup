local function float_config()
	-- Leave one cell on each side for the border while covering the editor.
	local width = vim.o.columns - 2
	local height = vim.o.lines - 2
	return {
		relative = "editor",
		row = 0,
		col = 0,
		width = width,
		height = height,
		style = "minimal",
		border = "rounded",
	}
end

local function open_terminal(command)
	local buffer = vim.api.nvim_create_buf(false, true)
	local window = vim.api.nvim_open_win(buffer, true, float_config())
	-- Keep the terminal centred when a tmux pane changes size.
	local resize_autocmd = vim.api.nvim_create_autocmd("VimResized", {
		callback = function()
			vim.api.nvim_win_set_config(window, float_config())
		end,
	})
	-- Closing the terminal float also removes its resize handler.
	vim.api.nvim_create_autocmd("WinClosed", {
		pattern = tostring(window),
		once = true,
		callback = function()
			vim.api.nvim_del_autocmd(resize_autocmd)
		end,
	})

	vim.bo[buffer].bufhidden = "wipe" -- Closing the float also stops its terminal job.
	vim.fn.jobstart(command, {
		term = true,
		on_exit = function()
			vim.schedule(function()
				if vim.api.nvim_win_is_valid(window) then
					vim.api.nvim_win_close(window, true)
				end
			end)
		end,
	})
	vim.cmd.startinsert()
end

vim.keymap.set("n", "<leader>t", function()
	open_terminal({ vim.o.shell })
end, { desc = "Open floating terminal" })

vim.keymap.set("n", "<leader>lg", function()
	open_terminal({ "lazygit" })
end, { desc = "Open LazyGit" })

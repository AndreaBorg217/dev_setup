-- Layout inspired by https://github.com/smnatale/nvim_native/blob/main/lua/statusline.lua
local modes = {
	n = "NORMAL",
	i = "INSERT",
	v = "VISUAL",
	V = "V-LINE",
	["\22"] = "V-BLOCK",
	c = "COMMAND",
	t = "TERMINAL",
	R = "REPLACE",
}

local mode_colours = {
	n = "Normal",
	i = "Insert",
	v = "Visual",
	V = "Visual",
	["\22"] = "Visual",
	c = "Command",
	R = "Replace",
}
local theme_background = vim.api.nvim_get_hl(0, { name = "Normal", link = false }).bg
for name, source in pairs({
	Normal = "Changed",
	Insert = "Added",
	Visual = "Conditional",
	Command = "WarningMsg",
	Replace = "ErrorMsg",
}) do
	local accent = vim.api.nvim_get_hl(0, { name = source, link = false }).fg
	vim.api.nvim_set_hl(0, "NextStatus" .. name, { fg = theme_background, bg = accent, bold = true })
end

vim.api.nvim_create_autocmd({ "BufEnter", "FocusGained" }, {
	callback = function()
		local file_dir = vim.fn.expand("%:p:h")
		local branch = vim.fn.systemlist({ "git", "-C", file_dir, "branch", "--show-current" })
		vim.b.next_git_branch = vim.v.shell_error == 0 and branch[1] or nil
	end,
})

function _G.next_statusline()
	local current_mode = vim.fn.mode()
	local mode = modes[current_mode] or current_mode:upper()
	local branch = vim.b.next_git_branch
	local colour = mode_colours[current_mode] or "Normal"
	local sections = { "%#NextStatus" .. colour .. "# " .. mode .. " %*" }
	if branch and branch ~= "" then
		table.insert(sections, "  " .. branch:gsub("%%", "%%%%"))
	end
	local filename = vim.bo.buftype == "terminal" and "%t" or "%f"
	table.insert(sections, "  " .. filename .. " %m%r%=")

	local counts = vim.diagnostic.count(0)
	for _, item in ipairs({
		{ vim.diagnostic.severity.ERROR, "DiagnosticError", "E" },
		{ vim.diagnostic.severity.WARN, "DiagnosticWarn", "W" },
	}) do
		if counts[item[1]] then
			table.insert(sections, "%#" .. item[2] .. "# " .. item[3] .. counts[item[1]] .. " %*")
		end
	end
	table.insert(sections, "  %y  %l:%c ")
	return table.concat(sections)
end

vim.opt.laststatus = 3 -- Show one shared status line across splits.
vim.opt.statusline = "%!v:lua.next_statusline()" -- Draw the native status line from buffer state.

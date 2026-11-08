vim.pack.add({
	"https://github.com/MunifTanjim/nui.nvim",
	"https://github.com/esmuellert/codediff.nvim",
	"https://github.com/georgeguimaraes/review.nvim",
}, { confirm = false })

require("review").setup({
	branch = { pick_base = true },
	export = {
		clear_on_close = false,
		header = table.concat({
			"I reviewed this diff. Use AskUserQuestion to ask whether to address the comments locally or submit them to a GitLab MR. If I choose GitLab, ask for the MR URL.",
			"",
			"Use the glab skill and API. Send each comment’s text verbatim, without its type or location in the body. ISSUE and SUGGESTION become discussions: use a file-level position when the range covers the whole file, otherwise use its line or line range. NOTE and PRAISE become MR notes.",
			"",
			"`~` marks the old side.",
			"",
			"Review comments:",
		}, "\n"),
	},
	keymaps = {
		readonly_add = "c",
		readonly_delete = "dd",
		readonly_toggle_reviewed = "r",
		list_comments = false,
		export_clipboard = "y",
		clear_comments = "X",
		close = false,
	},
})

local comments = require("review.comments")
function comments.delete_at_cursor()
	local file, line, side = require("review.hooks").get_cursor_position()
	local store = require("review.store")
	local comment = store.get_at_line(file, line, side)
	if not comment and line == 1 then
		comment = store.get_file_comment(file)
	end
	if not comment then
		return
	end
	store.delete(comment.id)
	require("review.marks").refresh()
end

local export = require("review.export")
function export.to_clipboard()
	export.deliver()
end

local review = require("review")
function review.clear()
	require("review.storage").clear()
	require("review.store").reset()
	require("review.reviewed").reset()
	require("review.marks").clear_all()
end

vim.api.nvim_create_autocmd("FileType", {
	pattern = "codediff-explorer",
	callback = function(event)
		vim.keymap.set("n", "r", function()
			local explorer = require("review.hooks").get_explorer(vim.api.nvim_get_current_tabpage())
			if explorer then
				require("review.reviewed").toggle_current(explorer)
			end
		end, { buffer = event.buf, desc = "Toggle file reviewed" })
	end,
})

vim.keymap.set("n", "<leader>rv", function()
	local tabpage = require("review.hooks").get_current_tabpage()
	if tabpage and vim.api.nvim_tabpage_is_valid(tabpage) then
		if vim.api.nvim_get_current_tabpage() == tabpage then
			require("codediff.ui.lifecycle").close(tabpage)
		else
			vim.api.nvim_set_current_tabpage(tabpage)
		end
	else
		require("review").open()
	end
end, { desc = "Toggle code review" })

vim.keymap.set("n", "<leader>rb", function()
	local tabpage = require("review.hooks").get_current_tabpage()
	if tabpage and vim.api.nvim_tabpage_is_valid(tabpage) then
		require("codediff.ui.lifecycle").close(tabpage)
	end
	require("review").open_branch()
end, { desc = "Review branches" })
vim.keymap.set("n", "<leader>rp", function()
	local buffer = vim.api.nvim_create_buf(false, true)
	local markdown = export.generate_markdown()
	local header = require("review.config").get().export.header .. "\n\n"
	if markdown:sub(1, #header) == header then
		markdown = markdown:sub(#header + 1)
	end
	vim.api.nvim_buf_set_lines(buffer, 0, -1, false, vim.split(markdown, "\n", { plain = true }))
	vim.bo[buffer].filetype = "markdown"
	vim.bo[buffer].modifiable = false
	vim.bo[buffer].bufhidden = "wipe"
	local window = vim.api.nvim_open_win(buffer, true, {
		relative = "editor",
		row = 1,
		col = 1,
		width = vim.o.columns - 4,
		height = vim.o.lines - 4,
		style = "minimal",
		border = "rounded",
	})
	vim.wo[window].wrap = true
	vim.wo[window].linebreak = true
	vim.keymap.set("n", "q", function()
		vim.api.nvim_win_close(window, true)
	end, { buffer = buffer, desc = "Close review preview" })
end, { desc = "Preview review comments" })

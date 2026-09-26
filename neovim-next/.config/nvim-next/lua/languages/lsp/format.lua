local M = {}

-- Replace only the changed hunks so diagnostics on untouched lines remain visible,
-- and cursor/undo state stays intact instead of being reset by a full buffer rewrite.
function M.apply_diff(bufnr, new_lines)
	local before = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
	local input = table.concat(before, "\n") .. "\n"
	local after_text = table.concat(new_lines, "\n") .. "\n"

	local hunks = vim.diff(input, after_text, { result_type = "indices" })
	for index = #hunks, 1, -1 do
		local hunk = hunks[index]
		local start = hunk[1] - (hunk[2] > 0 and 1 or 0)
		local replacement = {}
		for line = hunk[3], hunk[3] + hunk[4] - 1 do
			table.insert(replacement, new_lines[line])
		end
		vim.api.nvim_buf_set_lines(bufnr, start, start + hunk[2], false, replacement)
	end
end

-- Shared by docker.lua (compose files) and yaml.lua so yamlfmt setup exists in one place.
function M.format_yaml(bufnr)
	local before = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
	local input = table.concat(before, "\n") .. "\n"
	local after = vim.fn.systemlist({ "yamlfmt", "-in" }, input)
	if vim.v.shell_error ~= 0 then
		vim.notify("yamlfmt could not format this file", vim.log.levels.ERROR)
		return
	end
	M.apply_diff(bufnr, after)
end

function M.format_on_save(filetype, formatter_fn)
	local group_name = type(filetype) == "table" and table.concat(filetype, "_") or filetype

	vim.api.nvim_create_autocmd("FileType", {
		group = vim.api.nvim_create_augroup(group_name .. "_format", { clear = true }),
		pattern = filetype,
		callback = function(args)
			vim.keymap.set("n", "<leader>fmt", function()
				formatter_fn(args.buf)
			end, { buffer = args.buf, desc = "Format " .. group_name .. " file" })
			vim.api.nvim_create_autocmd("BufWritePre", {
				group = vim.api.nvim_create_augroup(group_name .. "_format_" .. args.buf, { clear = true }),
				buffer = args.buf,
				callback = function()
					if require("config").AUTO_FORMAT then
						formatter_fn(args.buf)
					end
				end,
			})
		end,
	})
end

return M

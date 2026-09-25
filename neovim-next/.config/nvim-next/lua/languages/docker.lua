-- Compose files need their own filetype so Docker's server receives the dockercompose language ID.
vim.filetype.add({
	filename = {
		["docker-compose.yml"] = "yaml.docker-compose",
		["docker-compose.yaml"] = "yaml.docker-compose",
		["compose.yml"] = "yaml.docker-compose",
		["compose.yaml"] = "yaml.docker-compose",
	},
})

local function format_docker(bufnr, command)
	local before = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
	local input = table.concat(before, "\n") .. "\n"
	local after = vim.fn.systemlist(command, input)
	if vim.v.shell_error ~= 0 then
		vim.notify(command[1] .. " could not format this file", vim.log.levels.ERROR)
		return
	end

	-- Replace changed lines only so diagnostics on untouched lines remain visible.
	local hunks = vim.diff(input, table.concat(after, "\n") .. "\n", { result_type = "indices" })
	for index = #hunks, 1, -1 do
		local hunk = hunks[index]
		local start = hunk[1] - (hunk[2] > 0 and 1 or 0)
		local replacement = {}
		for line = hunk[3], hunk[3] + hunk[4] - 1 do
			table.insert(replacement, after[line])
		end
		vim.api.nvim_buf_set_lines(bufnr, start, start + hunk[2], false, replacement)
	end
end

vim.api.nvim_create_autocmd("FileType", {
	group = vim.api.nvim_create_augroup("docker_format", { clear = true }),
	pattern = { "dockerfile", "yaml.docker-compose" },
	callback = function(args)
		local command = vim.bo[args.buf].filetype == "dockerfile" and { "dockerfmt", "--newline" } or { "yamlfmt", "-in" }
		vim.keymap.set("n", "<leader>fmt", function()
			format_docker(args.buf, command)
		end, { buffer = args.buf, desc = "Format Docker file" })
		vim.api.nvim_create_autocmd("BufWritePre", {
			group = vim.api.nvim_create_augroup("docker_format_" .. args.buf, { clear = true }),
			buffer = args.buf,
			callback = function()
				if require("config").AUTO_FORMAT then
					format_docker(args.buf, command)
				end
			end,
		})
	end,
})

vim.lsp.config("docker_language_server", {
	cmd = { "docker-language-server", "start", "--stdio" },
	filetypes = { "dockerfile", "yaml.docker-compose" },
	get_language_id = function(_, filetype)
		if filetype == "yaml.docker-compose" then
			return "dockercompose"
		end
		return filetype
	end,
	root_markers = { "Dockerfile", "docker-compose.yaml", "docker-compose.yml", "compose.yaml", "compose.yml", ".git" },
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
		vim.lsp.inlay_hint.enable(true, { bufnr = bufnr })
	end,
})

vim.lsp.enable("docker_language_server")

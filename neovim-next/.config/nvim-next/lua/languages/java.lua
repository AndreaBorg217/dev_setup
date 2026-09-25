local function format_java(bufnr)
	local before = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
	local input = table.concat(before, "\n") .. "\n"
	local command = { "palantir-java-format", "--palantir", "--assume-filename", vim.api.nvim_buf_get_name(bufnr), "-" }
	local after = vim.fn.systemlist(command, input)
	if vim.v.shell_error ~= 0 then
		vim.notify("Palantir could not format this Java file", vim.log.levels.ERROR)
		return
	end

	-- Changed hunks keep diagnostics on untouched lines in place.
	local hunks = vim.diff(input, table.concat(after, "\n") .. "\n", { result_type = "indices" })
	-- Clear Spring hints before edits so their old columns cannot render on shorter lines.
	local hints_enabled = vim.lsp.inlay_hint.is_enabled({ bufnr = bufnr })
	if hints_enabled then
		vim.lsp.inlay_hint.enable(false, { bufnr = bufnr })
	end
	for index = #hunks, 1, -1 do
		local hunk = hunks[index]
		local start = hunk[1] - (hunk[2] > 0 and 1 or 0)
		local replacement = {}
		for line = hunk[3], hunk[3] + hunk[4] - 1 do
			table.insert(replacement, after[line])
		end
		vim.api.nvim_buf_set_lines(bufnr, start, start + hunk[2], false, replacement)
	end
	if hints_enabled then
		vim.lsp.inlay_hint.enable(true, { bufnr = bufnr })
	end
end

vim.api.nvim_create_autocmd("FileType", {
	group = vim.api.nvim_create_augroup("java_format", { clear = true }),
	pattern = "java",
	callback = function(args)
		vim.keymap.set("n", "<leader>fmt", function()
			format_java(args.buf)
		end, { buffer = args.buf, desc = "Format Java file" })
		vim.api.nvim_create_autocmd("BufWritePre", {
			group = vim.api.nvim_create_augroup("java_format_" .. args.buf, { clear = true }),
			buffer = args.buf,
			callback = function()
				if require("config").AUTO_FORMAT then
					format_java(args.buf)
				end
			end,
		})
	end,
})

vim.lsp.config("jdtls", {
	cmd = function(dispatchers, config)
		-- Eclipse stores project metadata under -data, so each project needs its own workspace.
		local workspace = vim.fn.stdpath("cache") .. "/jdtls/" .. vim.fn.fnamemodify(config.root_dir, ":t")
		return vim.lsp.rpc.start({ "jdtls", "-data", workspace }, dispatchers)
	end,
	filetypes = { "java" },
	-- Prefer a nested Java project over the enclosing repository's Git root.
	root_markers = { { "mvnw", "gradlew", "settings.gradle", "settings.gradle.kts", "pom.xml", "build.gradle", "build.gradle.kts", "build.xml" }, ".git" },
	before_init = function(params)
		local bundles = require("spring_boot").java_extensions()
		local debug_jars = vim.fn.glob(
			vim.fn.stdpath("data") .. "/mason/share/java-debug-adapter/com.microsoft.java.debug.plugin-*.jar",
			false,
			true
		)
		vim.list_extend(bundles, debug_jars)
		params.initializationOptions = { bundles = bundles }
	end,
	settings = {
		java = {
			completion = { importOrder = { "java", "javax", "org", "com" } },
			format = { enabled = false },
			referencesCodeLens = { enabled = true },
			saveActions = { organizeImports = true },
			sources = { organizeImports = { starThreshold = 999, staticStarThreshold = 999 } },
		},
	},
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
		require("jdtls").setup_dap()
	end,
})

vim.lsp.enable("jdtls")

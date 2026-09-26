-- Spring property completion and Java awareness need the Spring Tools server and JDT LS extensions.
vim.pack.add({ "https://github.com/JavaHello/spring-boot.nvim" }, { confirm = false })

local spring_boot = require("spring_boot")
-- Spring Tools uses a non-web launch when its optional MCP server is disabled.
spring_boot.setup({
	jvm_args = { "-Dspring.main.web-application-type=NONE" },
	log_file = vim.fn.stdpath("state") .. "/spring-boot.log",
	-- Only start where the build actually declares a Spring Boot dependency.
	project_filter = function(root_dir)
		return require("spring_boot.util").has_spring_boot_dependency(root_dir)
	end,
	server = {
		on_attach = function(client, bufnr)
			vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
		end,
	},
})

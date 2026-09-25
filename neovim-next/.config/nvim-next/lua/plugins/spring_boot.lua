-- Spring property completion and Java awareness need the Spring Tools server and JDT LS extensions.
vim.pack.add({ "https://github.com/JavaHello/spring-boot.nvim" }, { confirm = false })

local spring_boot = require("spring_boot")
-- Spring Tools uses a non-web launch when its optional MCP server is disabled.
spring_boot.setup({
	jvm_args = { "-Dspring.main.web-application-type=NONE" },
	server = {
		on_attach = function(client, bufnr)
			vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
			vim.lsp.inlay_hint.enable(true, { bufnr = bufnr })
		end,
	},
})

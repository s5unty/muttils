" $Id$
" set up sigpager eg. in ~/.vim/after/ftplugin/mail.vim

" choose email signature, append at EOF, jump back to previous position
nnoremap <buffer> <LocalLeader>s m`:$r!sigpager<CR>:redr!<CR>``

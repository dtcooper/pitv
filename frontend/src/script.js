// Needed until https://github.com/alpinejs/alpine/pull/2968 is released

import Alpine from 'alpinejs/src'
import persist from '@alpinejs/persist/src'

window.Alpine = Alpine
Alpine.plugin(persist)
Alpine.start()

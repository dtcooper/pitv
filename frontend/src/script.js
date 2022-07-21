/* global DATA */

import Alpine from 'alpinejs'
import persist from '@alpinejs/persist'
import collapse from '@alpinejs/collapse'
import ReconnectingWebSocket from 'reconnecting-websocket'

Alpine.plugin(collapse)
Alpine.plugin(persist)
window.Alpine = Alpine

document.addEventListener('alpine:init', () => {
  let socket

  function sendJSON (data) {
    socket.send(JSON.stringify(data))
  }

  Alpine.store('notify', {
    alerts: [],
    id: 0,
    show (message, level = 'info', timeout = 5000) {
      if (!['info', 'success', 'warning', 'error'].includes(level)) {
        level = 'info'
      }
      const id = this.id++
      this.alerts.push({ message, level, id })
      setTimeout(() => { this.alerts = this.alerts.filter(value => value.id !== id) }, timeout)
    },
    icon (level) {
      switch (level) {
        case 'success':
          return 'mdi:check-circle'
        case 'warning':
          return 'mdi:alert'
        case 'error':
          return 'mdi:alert-octagon'
        default:
          return 'mdi:information'
      }
    }
  })

  Alpine.store('player', {
    imdb: {
      path: null,
      working: false,
      results: []
    },
    /* Copied from backend/api/player.py:Player._state */
    videos: null,
    currentlyPlaying: null,
    download: null,
    position: null,
    duration: null,
    playing: null,
    playRRated: null,

    init () {
      Alpine.effect(() => this.scrollToCurrentlyPlaying())
    },

    scrollToCurrentlyPlaying () {
      if (this.currentlyPlaying !== null) {
        this.scrollToVideo(this.currentlyPlaying)
      }
    },

    scrollToVideo (path, block = 'center', delay = 25) {
      const elem = document.getElementById(`playlist-item-${path}`)
      if (elem) {
        setTimeout(() => elem.scrollIntoView({ behavior: 'smooth', block }), delay)
      }
    },

    currentlyPlayingVideo (attr = null) {
      if (this.currentlyPlaying !== null) {
        for (const video of (this.videos || [])) {
          if (video.path === this.currentlyPlaying) {
            return attr === null ? video : video[attr]
          }
        }
      }
      return null
    },

    formatDuration (s, forceHour = false) {
      let d = ''
      if (s > 3600 || forceHour) {
        d = `${Math.floor(s / 3600)}:`
      }
      d += `${Math.floor((s % 3600) / 60)}:`.padStart(3, '0')
      d += `${s % 60}`.padStart(2, '0')
      return d
    },

    prettyDuration () {
      return this.formatDuration(this.duration)
    },

    prettyPosition () {
      return this.formatDuration(this.position, this.duration > 3600)
    },

    prettyTimeleft () {
      return this.formatDuration(this.duration - this.position, this.duration > 3600)
    },

    setPosition (seconds) {
      sendJSON({ position: seconds })
    },

    seek (seconds) {
      sendJSON({ seek: seconds })
    },

    playRandom () {
      sendJSON({ playRandom: true })
    },

    play (path) {
      sendJSON({ play: path })
    },

    update (path, data) {
      data.filename = path
      sendJSON({ update: data })
    },

    togglePlayRRated () {
      sendJSON({ togglePlayRRated: true })
    },

    toggleMute () {
      sendJSON({ toggleMute: true })
    },

    playPause () {
      sendJSON({ playPause: true })
    },

    searchImdb (path, title) {
      this.imdb.working = true
      sendJSON({ searchImdb: [path, title] })
    }
  })

  Alpine.store('persist', {
    // for some reason $persist doesn't work during conn.init(), so define these separately
    password: Alpine.$persist('').as('password'),
    showPowerOnWarning: Alpine.$persist(true).as('showPowerOnWarning')
  })

  Alpine.store('conn', {
    notify: Alpine.store('notify'),
    persist: Alpine.store('persist'),
    player: Alpine.store('player'),
    authorized: false,
    isAdmin: false,
    badPassword: true,
    enterPassword: false,
    hasSocketOpenedBefore: false,
    connected: false, // Final state, ready to use the player, set after first message
    interstitialDescription: 'Connecting',
    interstitialAlertClass: 'alert-info',
    socket: null,
    init () {
      const hash = new URLSearchParams(window.location.hash.substring(1))
      const hashPassword = hash.get('pw')

      if (hashPassword) {
        window.history.replaceState({}, document.title, '.') // Remove hash from URL
        this.persist.password = hashPassword
      }
      if (hash.get('warn')) {
        this.persist.showPowerOnWarning = true
      }

      let websocketPrefix
      if (DATA.DEBUG && DATA.WEBSOCKET_URL_DEV_OVERRIDE) {
        websocketPrefix = DATA.WEBSOCKET_URL_DEV_OVERRIDE
      } else {
        websocketPrefix = ((window.location.protocol === 'https:') ? 'wss://' : 'ws://') + DATA.DOMAIN_NAME
      }
      socket = new ReconnectingWebSocket(websocketPrefix.replace(/\/$/, '') + '/backend')

      socket.onopen = () => {
        this.badPassword = this.authorized = this.connected = false
        this.hasSocketOpenedBefore = true
        if (this.persist.password) {
          this.login()
        } else {
          this.enterPassword = true
          this.focusPassword()
        }
      }

      socket.onclose = socket.onerror = () => {
        if (this.hasSocketOpenedBefore) {
          this.interstitialDescription = 'Reconnecting'
          this.interstitialAlertClass = 'alert-error'
        } else {
          this.interstitialDescription = 'Problem connecting'
          this.interstitialAlertClass = 'alert-warning'
        }
        this.enterPassword = this.connected = false
      }

      socket.onmessage = (event) => {
        let message = event.data
        if (this.authorized) {
          message = JSON.parse(message)
          for (const key in message) {
            const value = message[key]
            if (key === 'notify') {
              this.notify.show(value.message, value.level || undefined, value.timeout || undefined)
            } else {
              this.player[key] = value
            }
          }
          this.connected = true
        } else {
          if (message === 'PASSWORD_ACCEPTED_USER' || message === 'PASSWORD_ACCEPTED_ADMIN') {
            this.authorized = true
            this.isAdmin = message === 'PASSWORD_ACCEPTED_ADMIN'
            this.interstitialDescription = 'Initializing'
            this.interstitialAlertClass = 'alert-success'
          } else { // PASSWORD_DENIED
            this.badPassword = this.enterPassword = true
            this.persist.password = ''
            this.focusPassword()
          }
        }
      }
    },

    login () {
      if (this.persist.password) {
        this.interstitialDescription = 'Authorizing'
        this.interstitialAlertClass = 'alert-info'
        this.enterPassword = false
        socket.send(this.persist.password)
      } else {
        this.badPassword = true
        this.focusPassword()
      }
    },

    focusPassword () {
      setTimeout(() => { document.getElementById('password-input').focus() }, 15)
    },

    shouldShowPowerOnWarning () {
      return this.hasSocketOpenedBefore && this.persist.showPowerOnWarning
    }
  })
})

Alpine.data('playlistItem', (video) => ({
  player: Alpine.store('player'),
  edit: false,
  titleEdit: '',
  descriptionEdit: '',
  imageEdit: '',
  isRRatedEdit: false,

  isPlaying () {
    return this.player.currentlyPlaying === video.path
  },
  isRRatedDisabled () {
    return video.isRRated && !this.player.playRRated
  },
  resetEdit (edit = true) {
    this.edit = edit
    this.titleEdit = video.title
    this.descriptionEdit = video.description
    this.isRRatedEdit = video.isRRated
    this.imageEdit = video.image
    if (edit) {
      this.player.scrollToVideo(video.path, 'start', 200)
    }
  },
  update () {
    this.player.update(video.path, {
      title: this.titleEdit || video.title,
      description: this.descriptionEdit,
      isRRated: this.isRRatedEdit,
      image: this.imageEdit
    })
    this.edit = false
  }
}))

Alpine.data('imdbModal', (video) => ({
  player: Alpine.store('player'),
  index: 0,
  useTitle: true,
  useDescription: true,
  useImage: true,
  reset () {
    this.index = 0
    this.useTitle = this.useDescription = this.useImage = true
    this.player.imdb.path = null
  },
  currentImdbVideo () {
    if (this.player.imdb.path === video.path) {
      if (this.index < this.player.imdb.results.length) {
        return this.player.imdb.results[this.index]
      }
    }
    return null
  },
  value (key, defaultValue = null) {
    const video = this.currentImdbVideo()
    if (video) {
      const value = video[key]
      return value === null ? defaultValue : value
    }
    return defaultValue
  },
  hasNext () {
    return this.index < (this.player.imdb.results.length - 1)
  },
  hasPrev () {
    return this.index > 0
  },
  done () {
    const title = this.value('title')
    const description = this.value('description')
    const image = this.value('image')
    if (this.useTitle) {
      this.titleEdit = title
    }
    if (this.useDescription && description) {
      this.descriptionEdit = description
    }
    if (this.useImage && image) {
      this.imageEdit = image
    }
    this.reset()
  }
}))

Alpine.start()

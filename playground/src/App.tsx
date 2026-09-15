import {
  type ChangeEvent,
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from 'react'
import './App.css'

type Tab = 'evidence' | 'assertions' | 'world'

type Health = {
  status: string
  service: string
  model: {
    status: string
    error: string | null
  }
  dense_recovery: {
    status: string
  }
}

type Evidence = {
  id: number
  session_id: string
  role: string
  content: string
  created_at: string
}

type Session = {
  session_id: string
  title: string
  message_count: number
  first_message_id: number
  last_message_id: number
  created_at: string
  updated_at: string
}

type MessageAttachment = {
  id: string
  ordinal: number
  original_filename: string
  media_type: string
  size_bytes: number
  retention_class: string
  blob_status: string
  created_at: string
  content_url: string | null
  preview_url?: string
}

type ChatMessage = {
  id: number
  session_id: string
  role: string
  content: string
  created_at: string
  attachments?: MessageAttachment[]
}

type SessionDetail = {
  session_id: string
  message_count: number
  returned_count: number
  has_more: boolean
  messages: ChatMessage[]
}

type ChatResponse = {
  reply: string | null
  status: {
    overall: string
  }
  error: string | null
}

type AttachmentUploadResponse = {
  attachment_id: string
  original_filename: string
  media_type: string
  size_bytes: number
  retention_class: string
  blob_status: string
}

const VISION_IMAGE_TYPES = new Set([
  'image/png',
  'image/jpeg',
])

const MAX_VISION_IMAGE_BYTES =
  16 * 1024 * 1024


const WELCOME_PROMPTS = [
  "What's on your mind?",
  "How are you doing today?",
  "What are you thinking about?",
  "What should we work on?",
  "Anything you want to talk about?",
  "Where should we pick up?",
  "What would you like to explore?",
  "How can I help today?",
]

function pickWelcomePrompt(current?: string) {
  const candidates = current
    ? WELCOME_PROMPTS.filter((prompt) => prompt !== current)
    : WELCOME_PROMPTS

  return candidates[
    Math.floor(Math.random() * candidates.length)
  ] ?? WELCOME_PROMPTS[0]
}


function App() {
  const [inspectOpen, setInspectOpen] = useState(false)
  const [conversationOpen, setConversationOpen] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const hour = new Date().getHours()
    return hour >= 7 && hour < 19 ? 'light' : 'dark'
  })
  const [tab, setTab] = useState<Tab>('evidence')
  const [evidence, setEvidence] = useState<Evidence[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState(false)
  const [sessions, setSessions] = useState<Session[]>([])
  const [selectedSession, setSelectedSession] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [selectedImage, setSelectedImage] =
    useState<File | null>(null)
  const [selectedImagePreview, setSelectedImagePreview] =
    useState<string | null>(null)
  const composerRef = useRef<HTMLTextAreaElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const messagesRef = useRef<HTMLDivElement | null>(null)
  const speechAudioRef = useRef<HTMLAudioElement | null>(null)
  const voiceAudioRef = useRef<HTMLAudioElement | null>(null)
  const [playingVoiceAttachmentId, setPlayingVoiceAttachmentId] = useState<string | null>(null)
  const [voiceTranscriptByAttachment, setVoiceTranscriptByAttachment] = useState<Record<string, string>>({})
  const [expandedVoiceTranscriptId, setExpandedVoiceTranscriptId] = useState<string | null>(null)
  const [voiceTranscriptLoadingId, setVoiceTranscriptLoadingId] = useState<string | null>(null)
  const [speakingMessageId, setSpeakingMessageId] =
    useState<number | null>(null)
  const [speechLoadingMessageId, setSpeechLoadingMessageId] =
    useState<number | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const voiceChunksRef = useRef<Blob[]>([])
  const recordingTimerRef = useRef<number | null>(null)
  const micLeaseTimerRef = useRef<number | null>(null)
  const recordingStartedAtRef = useRef<number | null>(null)
  const [recording, setRecording] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [composerExpanded, setComposerExpanded] = useState(false)
  const [sending, setSending] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [welcomePrompt, setWelcomePrompt] = useState(
    () => pickWelcomePrompt(),
  )



  useEffect(() => {
    return () => {
      if (recordingTimerRef.current !== null) {
        window.clearInterval(recordingTimerRef.current)
      }

      const recorder = mediaRecorderRef.current

      if (recorder && recorder.state !== 'inactive') {
        recorder.stop()
      }

      mediaStreamRef.current
        ?.getTracks()
        .forEach((track) => track.stop())
    }
  }, [])

  useEffect(() => {
    const viewport = window.visualViewport
    const root = document.documentElement

    if (!viewport) return

    const activeViewport = viewport

    function syncVisualViewport() {
      root.style.setProperty(
        '--corvus-visual-height',
        `${activeViewport.height}px`,
      )
      root.style.setProperty(
        '--corvus-visual-top',
        `${activeViewport.offsetTop}px`,
      )
    }

    function restoreViewportAfterFocus() {
      window.setTimeout(() => {
        window.scrollTo(0, 0)
        syncVisualViewport()
      }, 80)
    }

    syncVisualViewport()

    viewport.addEventListener('resize', syncVisualViewport)
    viewport.addEventListener('scroll', syncVisualViewport)
    window.addEventListener('orientationchange', syncVisualViewport)
    document.addEventListener('focusout', restoreViewportAfterFocus)

    return () => {
      viewport.removeEventListener('resize', syncVisualViewport)
      viewport.removeEventListener('scroll', syncVisualViewport)
      window.removeEventListener('orientationchange', syncVisualViewport)
      document.removeEventListener(
        'focusout',
        restoreViewportAfterFocus,
      )
    }
  }, [])


  useEffect(() => {
    async function loadHealth() {
      try {
        const response = await fetch('/api/health')
        if (!response.ok) throw new Error()

        const data: Health = await response.json()
        setHealth(data)
        setHealthError(false)
      } catch {
        setHealth(null)
        setHealthError(true)
      }
    }

    loadHealth()
    const timer = window.setInterval(loadHealth, 10000)

    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    async function loadSessions() {
      try {
        const response = await fetch('/api/sessions')
        if (!response.ok) return

        const data: Session[] = await response.json()
        setSessions(data)
      } catch {
        setSessions([])
      }
    }

    loadSessions()
  }, [])


  function isCompactLayout() {
    return window.matchMedia('(max-width: 900px)').matches
  }

  async function selectSession(sessionId: string) {
    setDraft('')
    clearSelectedImage()
    setChatError(null)
    setSelectedSession(sessionId)

    if (!sessionId) {
      setChatMessages([])
      return
    }

    try {
      const response = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}`,
      )

      if (!response.ok) {
        setChatMessages([])
        return
      }

      const data: SessionDetail = await response.json()
      setChatMessages(data.messages)
    } catch {
      setChatMessages([])
    }
  }

  useEffect(() => {
    const textarea = composerRef.current
    if (!textarea) return

    textarea.style.height = 'auto'

    const scrollHeight = textarea.scrollHeight
    const nextHeight = Math.min(scrollHeight, 180)

    textarea.style.height = `${nextHeight}px`
    textarea.style.overflowY =
      scrollHeight > 180 ? 'auto' : 'hidden'

    setComposerExpanded(scrollHeight > 44)
  }, [draft])

  function scrollChatToBottom() {
    requestAnimationFrame(() => {
      const container = messagesRef.current
      if (!container) return

      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth',
      })
    })
  }

  useEffect(() => {
    if (chatMessages.length === 0) return

    requestAnimationFrame(() => {
      const container = messagesRef.current
      if (!container) return

      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth',
      })
    })
  }, [chatMessages])

  useEffect(() => {
    const preview = selectedImagePreview

    return () => {
      if (preview) {
        URL.revokeObjectURL(preview)
      }
    }
  }, [selectedImagePreview])

  useEffect(() => {
    return () => {
      if (micLeaseTimerRef.current !== null) {
        window.clearTimeout(
          micLeaseTimerRef.current,
        )
        micLeaseTimerRef.current = null
      }
    }
  }, [])

  function clearSelectedImage() {
    setSelectedImage(null)
    setSelectedImagePreview(null)

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  function handleImageSelected(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file = event.target.files?.[0]

    if (!file) return

    if (!VISION_IMAGE_TYPES.has(file.type)) {
      event.target.value = ''
      setChatError(
        'Vision v1 supports PNG and JPEG images only.',
      )
      return
    }

    if (file.size > MAX_VISION_IMAGE_BYTES) {
      event.target.value = ''
      setChatError(
        'This image is larger than the 16 MiB Vision v1 limit.',
      )
      return
    }

    setSelectedImage(file)
    setSelectedImagePreview(
      URL.createObjectURL(file),
    )
    setChatError(null)

    window.setTimeout(() => {
      composerRef.current?.focus()
    }, 0)
  }

  function formatRecordingTime(totalSeconds: number) {
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60

    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  function cancelMicLeaseTimer() {
    if (micLeaseTimerRef.current !== null) {
      window.clearTimeout(
        micLeaseTimerRef.current,
      )
      micLeaseTimerRef.current = null
    }
  }

  function releaseMicrophoneStream() {
    cancelMicLeaseTimer()

    mediaStreamRef.current
      ?.getTracks()
      .forEach((track) => track.stop())

    mediaStreamRef.current = null
  }

  function scheduleMicrophoneRelease() {
    cancelMicLeaseTimer()

    const stream = mediaStreamRef.current

    if (!stream) return

    micLeaseTimerRef.current =
      window.setTimeout(() => {
        if (mediaStreamRef.current !== stream) {
          return
        }

        stream
          .getTracks()
          .forEach((track) => track.stop())

        mediaStreamRef.current = null
        micLeaseTimerRef.current = null
      }, 30_000)
  }

  function clearVoiceCaptureResources(
    keepMicrophone = false,
  ) {
    if (recordingTimerRef.current !== null) {
      window.clearInterval(recordingTimerRef.current)
      recordingTimerRef.current = null
    }

    if (keepMicrophone) {
      cancelMicLeaseTimer()
    } else {
      releaseMicrophoneStream()
    }

    mediaRecorderRef.current = null
    recordingStartedAtRef.current = null
  }

  async function startVoiceRecording() {
    if (sending || recording) return

    if (selectedImage) {
      setChatError(
        'Remove the image before starting a voice message.',
      )
      return
    }

    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === 'undefined'
    ) {
      setChatError(
        'Voice recording is not supported in this browser.',
      )
      return
    }

    try {
      stopSpeechPlayback()
      setChatError(null)

      cancelMicLeaseTimer()

      let stream = mediaStreamRef.current

      const hasLiveAudioTrack =
        stream
          ?.getAudioTracks()
          .some(
            (track) =>
              track.readyState === 'live',
          ) ?? false

      if (!stream || !hasLiveAudioTrack) {
        stream
          ?.getTracks()
          .forEach((track) => track.stop())

        stream =
          await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
          })

        mediaStreamRef.current = stream
      }

      const preferredMimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/mp4',
      ]

      const mimeType =
        preferredMimeTypes.find((candidate) =>
          MediaRecorder.isTypeSupported(candidate),
        )

      const recorder = mimeType
        ? new MediaRecorder(stream, {
            mimeType,
          })
        : new MediaRecorder(stream)

      voiceChunksRef.current = []
      mediaStreamRef.current = stream
      mediaRecorderRef.current = recorder

      recorder.addEventListener(
        'dataavailable',
        (event) => {
          if (event.data.size > 0) {
            voiceChunksRef.current.push(
              event.data,
            )
          }
        },
      )

      recorder.start(250)

      const startedAt = Date.now()

      recordingStartedAtRef.current =
        startedAt

      setRecordingSeconds(0)
      setRecording(true)

      recordingTimerRef.current =
        window.setInterval(() => {
          setRecordingSeconds(
            Math.floor(
              (Date.now() - startedAt) /
                1000,
            ),
          )
        }, 250)

    } catch (error) {
      clearVoiceCaptureResources()

      setRecording(false)
      setRecordingSeconds(0)

      setChatError(
        error instanceof Error
          ? `Microphone unavailable: ${error.message}`
          : 'Microphone unavailable.',
      )
    }
  }

  async function finishVoiceRecording(
    shouldSend: boolean,
  ) {
    const recorder =
      mediaRecorderRef.current

    if (!recorder) return

    if (recordingTimerRef.current !== null) {
      window.clearInterval(
        recordingTimerRef.current,
      )
      recordingTimerRef.current = null
    }

    const mimeType =
      recorder.mimeType || 'audio/webm'

    let voiceBlob: Blob

    try {
      voiceBlob = await new Promise<Blob>(
        (resolve, reject) => {
          const finish = () => {
            resolve(
              new Blob(
                voiceChunksRef.current,
                {
                  type: mimeType,
                },
              ),
            )
          }

          recorder.addEventListener(
            'stop',
            finish,
            { once: true },
          )

          try {
            if (
              recorder.state !== 'inactive'
            ) {
              recorder.stop()
            } else {
              finish()
            }
          } catch (error) {
            reject(error)
          }
        },
      )
    } catch (error) {
      clearVoiceCaptureResources()
      voiceChunksRef.current = []
      setRecording(false)
      setRecordingSeconds(0)

      setChatError(
        error instanceof Error
          ? error.message
          : 'Unable to finish voice recording.',
      )
      return
    }

    clearVoiceCaptureResources(true)
    voiceChunksRef.current = []

    setRecording(false)
    setRecordingSeconds(0)

    if (!shouldSend) {
      scheduleMicrophoneRelease()
      setChatError(null)
      return
    }

    if (voiceBlob.size === 0) {
      scheduleMicrophoneRelease()

      setChatError(
        'The voice recording was empty.',
      )
      return
    }

    await sendVoiceBlob(voiceBlob)
  }

  async function sendVoiceBlob(
    voiceBlob: Blob,
  ) {
    if (sending) return

    const wasNew = !selectedSession
    const sessionId =
      selectedSession || `chat-${Date.now()}`

    const previousMessages =
      chatMessages

    const optimisticMessage: ChatMessage = {
      id: -Date.now(),
      session_id: sessionId,
      role: 'user',
      content: '[Voice message]',
      created_at: new Date().toISOString(),
      attachments: [],
    }

    setChatMessages([
      ...previousMessages,
      optimisticMessage,
    ])

    setSending(true)
    setChatError(null)
    scrollChatToBottom()

    if (wasNew) {
      setSelectedSession(sessionId)
    }

    try {
      const mediaType =
        voiceBlob.type ||
        'audio/webm'

      const normalizedMediaType =
        mediaType
          .split(';', 1)[0]
          .toLowerCase()

      const extension =
        normalizedMediaType === 'audio/mp4'
          ? 'm4a'
          : normalizedMediaType ===
              'audio/ogg'
            ? 'ogg'
            : 'webm'

      const filename =
        `voice-${Date.now()}.${extension}`

      const uploadResponse =
        await fetch(
          `/api/attachments?filename=${encodeURIComponent(filename)}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': mediaType,
            },
            body: voiceBlob,
          },
        )

      const uploadData =
        (await uploadResponse.json()) as
          AttachmentUploadResponse & {
            detail?: string
          }

      if (
        !uploadResponse.ok ||
        !uploadData.attachment_id
      ) {
        throw new Error(
          uploadData.detail ||
            'Corvus could not upload the voice recording.',
        )
      }

      const response =
        await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type':
              'application/json',
          },
          body: JSON.stringify({
            session_id: sessionId,
            message: '',
            attachment_id:
              uploadData.attachment_id,
            attachment_mode: 'voice',
          }),
        })

      const data: ChatResponse =
        await response.json()

      if (
        !response.ok ||
        !data.reply ||
        data.status?.overall ===
          'FAILED'
      ) {
        throw new Error(
          data.error ||
            'Corvus could not complete the voice turn.',
        )
      }

      await selectSession(sessionId)
      scrollChatToBottom()

      const sessionsResponse =
        await fetch('/api/sessions')

      if (sessionsResponse.ok) {
        const sessionData: Session[] =
          await sessionsResponse.json()

        setSessions(sessionData)
      }

    } catch (error) {
      let canonicalRecovered = false

      try {
        const historyResponse =
          await fetch(
            `/api/sessions/${encodeURIComponent(sessionId)}`,
          )

        if (historyResponse.ok) {
          const history: SessionDetail =
            await historyResponse.json()

          setSelectedSession(sessionId)
          setChatMessages(
            history.messages,
          )

          canonicalRecovered = true
        }
      } catch {
        // Fall through to local rollback.
      }

      if (!canonicalRecovered) {
        setChatMessages(
          previousMessages,
        )

        if (wasNew) {
          setSelectedSession('')
        }
      }

      setChatError(
        error instanceof Error
          ? error.message
          : 'Unable to send voice message.',
      )

    } finally {
      setSending(false)
      scheduleMicrophoneRelease()
    }
  }

  function stopVoicePlayback() {
    const audio = voiceAudioRef.current

    if (audio) {
      audio.pause()
      audio.removeAttribute('src')
      audio.load()
      voiceAudioRef.current = null
    }

    setPlayingVoiceAttachmentId(null)
  }

  async function playVoiceAttachment(
    attachmentId: string,
    contentUrl: string,
  ) {
    if (
      voiceAudioRef.current &&
      playingVoiceAttachmentId === attachmentId
    ) {
      stopVoicePlayback()
      return
    }

    stopVoicePlayback()
    stopSpeechPlayback()

    const audio = new Audio(contentUrl)

    voiceAudioRef.current = audio
    setPlayingVoiceAttachmentId(
      attachmentId,
    )

    audio.addEventListener(
      'ended',
      () => {
        if (voiceAudioRef.current === audio) {
          voiceAudioRef.current = null
          setPlayingVoiceAttachmentId(
            null,
          )
        }
      },
      { once: true },
    )

    audio.addEventListener(
      'error',
      () => {
        if (voiceAudioRef.current === audio) {
          voiceAudioRef.current = null
          setPlayingVoiceAttachmentId(
            null,
          )
        }

        setChatError(
          'Unable to play this voice message.',
        )
      },
      { once: true },
    )

    try {
      await audio.play()
    } catch (error) {
      stopVoicePlayback()

      setChatError(
        error instanceof Error
          ? error.message
          : 'Unable to play this voice message.',
      )
    }
  }

  async function toggleVoiceTranscript(
    attachmentId: string,
  ) {
    if (
      expandedVoiceTranscriptId ===
      attachmentId
    ) {
      setExpandedVoiceTranscriptId(null)
      return
    }

    if (
      voiceTranscriptByAttachment[
        attachmentId
      ]
    ) {
      setExpandedVoiceTranscriptId(
        attachmentId,
      )
      return
    }

    setVoiceTranscriptLoadingId(
      attachmentId,
    )

    try {
      const response = await fetch(
        `/api/attachments/${encodeURIComponent(
          attachmentId,
        )}/transcript`,
      )

      const data = (
        await response.json()
      ) as {
        content?: string
        detail?: string
      }

      if (!response.ok || !data.content) {
        throw new Error(
          data.detail ||
            'Transcript is not available.',
        )
      }

      setVoiceTranscriptByAttachment(
        (current) => ({
          ...current,
          [attachmentId]:
            data.content as string,
        }),
      )

      setExpandedVoiceTranscriptId(
        attachmentId,
      )
    } catch (error) {
      setChatError(
        error instanceof Error
          ? error.message
          : 'Unable to load transcript.',
      )
    } finally {
      setVoiceTranscriptLoadingId(null)
    }
  }

  function stopSpeechPlayback() {
    const audio = speechAudioRef.current

    if (audio) {
      audio.pause()
      audio.removeAttribute('src')
      audio.load()
      speechAudioRef.current = null
    }

    setSpeakingMessageId(null)
    setSpeechLoadingMessageId(null)
  }

  function playAssistantMessage(messageId: number) {
    if (
      speechAudioRef.current &&
      (
        speakingMessageId === messageId ||
        speechLoadingMessageId === messageId
      )
    ) {
      stopSpeechPlayback()
      return
    }

    stopSpeechPlayback()

    const audio = new Audio(`/api/tts/${messageId}`)
    audio.preload = 'none'

    speechAudioRef.current = audio
    setSpeechLoadingMessageId(messageId)

    audio.onplaying = () => {
      if (speechAudioRef.current !== audio) return

      setSpeechLoadingMessageId(null)
      setSpeakingMessageId(messageId)
    }

    audio.onended = () => {
      if (speechAudioRef.current !== audio) return

      speechAudioRef.current = null
      setSpeechLoadingMessageId(null)
      setSpeakingMessageId(null)
    }

    audio.onerror = () => {
      if (speechAudioRef.current !== audio) return

      speechAudioRef.current = null
      setSpeechLoadingMessageId(null)
      setSpeakingMessageId(null)
      setChatError(
        'Voice playback failed. The text reply is still available.',
      )
    }

    void audio.play().catch(() => {
      if (speechAudioRef.current !== audio) return

      speechAudioRef.current = null
      setSpeechLoadingMessageId(null)
      setSpeakingMessageId(null)
      setChatError(
        'Voice playback could not start. The text reply is still available.',
      )
    })
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const message = draft.trim()
    const image = selectedImage

    if (!message || sending) return

    const wasNew = !selectedSession
    const sessionId = selectedSession || `chat-${Date.now()}`
    const previousMessages = chatMessages

    const optimisticPreview =
      image && selectedImagePreview
        ? selectedImagePreview
        : undefined

    const optimisticMessage: ChatMessage = {
      id: -Date.now(),
      session_id: sessionId,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
      attachments:
        image && optimisticPreview
          ? [
              {
                id: 'pending',
                ordinal: 0,
                original_filename: image.name,
                media_type: image.type,
                size_bytes: image.size,
                retention_class: 'PENDING',
                blob_status: 'PRESENT',
                created_at: new Date().toISOString(),
                content_url: null,
                preview_url: optimisticPreview,
              },
            ]
          : [],
    }

    /*
     * Optimistic UI:
     * acknowledge the user's send immediately while SQLite remains
     * the canonical source once the backend turn completes.
     */
    setDraft('')
    setSelectedImage(null)

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }

    setChatMessages([
      ...previousMessages,
      optimisticMessage,
    ])
    setSending(true)
    setChatError(null)
    scrollChatToBottom()

    if (wasNew) {
      setSelectedSession(sessionId)
    }

    let attachmentId: string | undefined

    if (image) {
      try {
        const uploadResponse = await fetch(
          `/api/attachments?filename=${encodeURIComponent(image.name)}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': image.type,
            },
            body: image,
          },
        )

        const uploadData =
          (await uploadResponse.json()) as
            AttachmentUploadResponse & {
              detail?: string
            }

        if (
          !uploadResponse.ok ||
          !uploadData.attachment_id
        ) {
          throw new Error(
            uploadData.detail ||
              'Corvus could not upload the image.',
          )
        }

        attachmentId =
          uploadData.attachment_id
      } catch (error) {
        setChatMessages(previousMessages)
        setDraft(message)

        if (image) {
          setSelectedImage(image)
        }

        if (wasNew) {
          setSelectedSession('')
        }

        setChatError(
          error instanceof Error
            ? error.message
            : 'Unable to upload the image.',
        )

        setSending(false)
        return
      }
    }

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          message,
          ...(attachmentId
            ? {
                attachment_id: attachmentId,
              }
            : {}),
        }),
      })

      const data: ChatResponse = await response.json()

      if (
        !response.ok ||
        !data.reply ||
        data.status?.overall === 'FAILED'
      ) {
        throw new Error(
          data.error || 'Corvus could not complete the turn.',
        )
      }

      /*
       * Replace the temporary optimistic message with canonical
       * SQLite-backed session history.
       */
      await selectSession(sessionId)
      scrollChatToBottom()

      const sessionsResponse = await fetch('/api/sessions')
      if (sessionsResponse.ok) {
        const sessionData: Session[] =
          await sessionsResponse.json()
        setSessions(sessionData)
      }
    } catch (error) {
      /*
       * Corvus commits user evidence before model generation.
       * If the backend received the message but generation failed,
       * preserve whatever SQLite actually contains.
       */
      let canonicalRecovered = false

      try {
        const historyResponse = await fetch(
          `/api/sessions/${encodeURIComponent(sessionId)}`,
        )

        if (historyResponse.ok) {
          const history: SessionDetail =
            await historyResponse.json()

          setSelectedSession(sessionId)
          setChatMessages(history.messages)
          canonicalRecovered = true
        }
      } catch {
        // Fall through to local rollback below.
      }

      /*
       * If no canonical session exists, the send likely never reached
       * Corvus. Restore the draft so the user can retry safely.
       */
      if (!canonicalRecovered) {
        setChatMessages(previousMessages)
        setDraft(message)

        if (image) {
          setSelectedImage(image)
        }

        if (wasNew) {
          setSelectedSession('')
        }
      }

      setChatError(
        error instanceof Error
          ? error.message
          : 'Unable to reach Corvus.',
      )
    } finally {
      setSending(false)
    }
  }

  async function openInspector() {
    const response = await fetch('/api/evidence')
    const data = await response.json()
    setEvidence(data)
    if (isCompactLayout()) setConversationOpen(false)
    setInspectOpen(true)
  }

  return (
    <main className="corvus-app" data-theme={theme}>
      <header className="topbar">
        <div className="topbar-brand">
          <button
            type="button"
            className={`ghost-button sidebar-toggle menu-toggle ${
              conversationOpen ? 'open' : ''
            }`}
            aria-label={
              conversationOpen
                ? 'Close conversations'
                : 'Open conversations'
            }
            onClick={() => {
              if (isCompactLayout()) setInspectOpen(false)
              setConversationOpen(!conversationOpen)
            }}
          >
            <span className="menu-icon" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
          </button>

          <div>
            <span className="eyebrow">CORVUS</span>
            <h1>Memory Playground</h1>
          </div>
        </div>

        <div className="topbar-actions">
          <span
            className={`status ${
              healthError
                ? 'health-offline'
                : !health
                  ? 'health-checking'
                  : health.status === 'OK'
                    ? 'health-healthy'
                    : 'health-degraded'
            }`}
            title={
              healthError
                ? 'Local · Offline'
                : !health
                  ? 'Local · Checking'
                  : `Local · ${
                      health.status === 'OK' ? 'Healthy' : 'Degraded'
                    } · Model ${health.model.status} · Retrieval ${
                      health.dense_recovery.status
                    }`
            }
          >
            <span className="status-dot" aria-hidden="true" />
            <span>Local</span>
          </span>

          <button
            type="button"
            className="ghost-button theme-toggle"
            aria-label={
              theme === 'dark'
                ? 'Switch to light mode'
                : 'Switch to dark mode'
            }
            title={
              theme === 'dark'
                ? 'Light mode'
                : 'Dark mode'
            }
            onClick={() =>
              setTheme(theme === 'dark' ? 'light' : 'dark')
            }
          >
            {theme === 'dark' ? (
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2" />
                <path d="M12 20v2" />
                <path d="m4.93 4.93 1.41 1.41" />
                <path d="m17.66 17.66 1.41 1.41" />
                <path d="M2 12h2" />
                <path d="M20 12h2" />
                <path d="m6.34 17.66-1.41 1.41" />
                <path d="m19.07 4.93-1.41 1.41" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3 6.5 6.5 0 0 0 21 12.8Z" />
              </svg>
            )}
          </button>

          <button
            type="button"
            className={`ghost-button inspect-toggle ${
              inspectOpen ? 'active' : ''
            }`}
            aria-label="Toggle memory inspector"
            title="Memory Inspector"
            onClick={() => {
              if (inspectOpen) {
                setInspectOpen(false)
              } else {
                openInspector()
              }
            }}
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <path d="M15 4v16" />
            </svg>
          </button>
        </div>
      </header>

      {conversationOpen && (
        <button
          type="button"
          className="drawer-backdrop"
          aria-label="Close conversations"
          onClick={() => setConversationOpen(false)}
        />
      )}

      <div
        className={`workspace ${
          conversationOpen ? 'conversation-open' : ''
        } ${inspectOpen ? 'inspector-open' : ''}`}
      >
        <aside
          className={`conversation-sidebar ${conversationOpen ? 'open' : ''}`}
        >
          <div className="conversation-sidebar-header">
            <span>Conversations</span>
          </div>

          <button
            type="button"
            className="new-chat-button"
            onClick={() => {
              setWelcomePrompt((current) => pickWelcomePrompt(current))
              selectSession('')
              if (isCompactLayout()) setConversationOpen(false)
            }}
          >
            + New chat
          </button>

          <div className="conversation-list">
            {sessions.map((session) => (
              <button
                type="button"
                key={session.session_id}
                className={
                  selectedSession === session.session_id
                    ? 'conversation-item active'
                    : 'conversation-item'
                }
                onClick={() => {
                  selectSession(session.session_id)
                  if (isCompactLayout()) setConversationOpen(false)
                }}
              >
                <span title={session.title}>{session.title}</span>
                <small>{session.message_count} messages</small>
              </button>
            ))}
          </div>
        </aside>

        <section className="chat-panel">
          <div className="messages" ref={messagesRef}>
          {chatMessages.length === 0 && !sending ? (
            <div className="welcome">
              <h2>Corvus</h2>
              <p>{welcomePrompt}</p>
            </div>
          ) : (
            <div className="chat-history">
              {chatMessages.map((message) => (
                <article
                  className={`chat-message ${message.role}`}
                  key={message.id}
                >
                  <div className="message-body">
                    {message.attachments?.some(
                      (attachment) =>
                        attachment.media_type
                          .toLowerCase()
                          .startsWith('image/'),
                    ) ? (
                      <div className="message-attachments">
                        {message.attachments
                          .filter(
                            (attachment) =>
                              attachment.media_type
                                .toLowerCase()
                                .startsWith('image/'),
                          )
                          .map(
                          (attachment) => {
                            const imageUrl =
                              attachment.preview_url ||
                              attachment.content_url

                            return (
                              <div
                                className="message-attachment"
                                key={`${message.id}-${attachment.id}-${attachment.ordinal}`}
                              >
                                {imageUrl &&
                                attachment.blob_status ===
                                  'PRESENT' ? (
                                  <img
                                    src={imageUrl}
                                    alt={
                                      attachment.original_filename ||
                                      'Attached image'
                                    }
                                    className="message-attachment-image"
                                  />
                                ) : (
                                  <div className="message-attachment-unavailable">
                                    <span>Image</span>
                                    <small>
                                      No longer retained
                                    </small>
                                  </div>
                                )}
                              </div>
                            )
                          },
                        )}
                      </div>
                    ) : null}

                    {message.role === 'user' &&
                    message.attachments?.some(
                      (attachment) =>
                        attachment.media_type
                          .toLowerCase()
                          .startsWith('audio/'),
                    ) ? (
                      <div className="voice-message-list">
                        {message.attachments
                          .filter(
                            (attachment) =>
                              attachment.media_type
                                .toLowerCase()
                                .startsWith('audio/'),
                          )
                          .map((attachment) => {
                            const isPlaying =
                              playingVoiceAttachmentId ===
                              attachment.id

                            const transcript =
                              voiceTranscriptByAttachment[
                                attachment.id
                              ]

                            const transcriptOpen =
                              expandedVoiceTranscriptId ===
                              attachment.id

                            return (
                              <div
                                className={`voice-message-card${
                                  isPlaying
                                    ? ' playing'
                                    : ''
                                }`}
                                key={`${message.id}-voice-${attachment.id}`}
                              >
                                <div className="voice-message-main">
                                  <button
                                    type="button"
                                    className="voice-message-play"
                                    disabled={
                                      attachment.blob_status !==
                                        'PRESENT' ||
                                      !attachment.content_url
                                    }
                                    onClick={() => {
                                      if (
                                        attachment.content_url
                                      ) {
                                        void playVoiceAttachment(
                                          attachment.id,
                                          attachment.content_url,
                                        )
                                      }
                                    }}
                                    aria-label={
                                      isPlaying
                                        ? 'Stop voice message'
                                        : 'Play voice message'
                                    }
                                    title={
                                      isPlaying
                                        ? 'Stop'
                                        : 'Play'
                                    }
                                  >
                                    {isPlaying ? (
                                      <span className="voice-stop-symbol" />
                                    ) : (
                                      <svg
                                        viewBox="0 0 24 24"
                                        aria-hidden="true"
                                      >
                                        <path d="M8 5.5v13l10-6.5-10-6.5Z" />
                                      </svg>
                                    )}
                                  </button>

                                  <div
                                    className="voice-message-wave"
                                    aria-hidden="true"
                                  >
                                    {Array.from({
                                      length: 22,
                                    }).map(
                                      (_, index) => (
                                        <i
                                          key={index}
                                          style={{
                                            animationDelay:
                                              `${(
                                                index %
                                                7
                                              ) * 55}ms`,
                                          }}
                                        />
                                      ),
                                    )}
                                  </div>
                                </div>

                                <button
                                  type="button"
                                  className="voice-transcript-toggle"
                                  onClick={() =>
                                    void toggleVoiceTranscript(
                                      attachment.id,
                                    )
                                  }
                                  disabled={
                                    voiceTranscriptLoadingId ===
                                    attachment.id
                                  }
                                >
                                  {voiceTranscriptLoadingId ===
                                  attachment.id
                                    ? 'Loading…'
                                    : transcriptOpen
                                      ? 'Hide transcript'
                                      : 'Transcript'}
                                </button>

                                {transcriptOpen &&
                                transcript ? (
                                  <div className="voice-transcript">
                                    {transcript}
                                  </div>
                                ) : null}
                              </div>
                            )
                          })}
                      </div>
                    ) : null}

                    {!(
                      message.role === 'user' &&
                      message.content ===
                        '[Voice message]' &&
                      message.attachments?.some(
                        (attachment) =>
                          attachment.media_type
                            .toLowerCase()
                            .startsWith(
                              'audio/',
                            ),
                      )
                    ) ? (
                      <p>{message.content}</p>
                    ) : null}

                    {message.role === 'assistant' ? (
                      <div className="message-actions">
                        <button
                          type="button"
                          className={`message-speech-button${
                            speakingMessageId === message.id
                              ? ' playing'
                              : ''
                          }${
                            speechLoadingMessageId === message.id
                              ? ' loading'
                              : ''
                          }`}
                          onClick={() =>
                            playAssistantMessage(message.id)
                          }
                          aria-label={
                            speakingMessageId === message.id ||
                            speechLoadingMessageId === message.id
                              ? 'Stop voice reply'
                              : 'Play voice reply'
                          }
                          aria-pressed={
                            speakingMessageId === message.id
                          }
                          aria-busy={
                            speechLoadingMessageId === message.id
                          }
                          title={
                            speakingMessageId === message.id ||
                            speechLoadingMessageId === message.id
                              ? 'Stop'
                              : 'Read aloud'
                          }
                        >
                          <svg
                            viewBox="0 0 24 24"
                            aria-hidden="true"
                          >
                            <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" />
                            <path d="M15 9a4 4 0 0 1 0 6" />
                            <path d="M17.5 6.5a7.5 7.5 0 0 1 0 11" />
                          </svg>
                        </button>
                      </div>
                    ) : null}
                  </div>
                </article>
              ))}

              {sending && (
                <article className="chat-message assistant thinking-message">
                  <div className="message-body">
                    <div
                      className="thinking-indicator"
                      aria-label="Corvus is thinking"
                    >
                      <span>Thinking</span>
                      <i />
                    </div>
                  </div>
                </article>
              )}
            </div>
          )}
        </div>

        <form
          className={`composer ${
            chatMessages.length === 0
              ? 'composer-new'
              : 'composer-established'
          } ${
            composerExpanded || selectedImage
              ? 'composer-expanded'
              : 'composer-single'
          } ${
            selectedImage
              ? 'composer-has-attachment'
              : ''
          } ${
            recording
              ? 'composer-recording'
              : ''
          }`}
          onSubmit={sendMessage}
        >
          {recording ? (
            <div
              className="voice-recording-strip"
              role="status"
              aria-label="Recording voice message"
            >
              <button
                type="button"
                className="voice-recording-cancel"
                aria-label="Cancel voice recording"
                title="Cancel"
                onClick={() => {
                  void finishVoiceRecording(false)
                }}
              >
                ×
              </button>

              <div
                className="voice-recording-wave"
                aria-hidden="true"
              >
                {Array.from(
                  { length: 22 },
                  (_, index) => (
                    <i key={index} />
                  ),
                )}
              </div>

              <span className="voice-recording-time">
                {formatRecordingTime(
                  recordingSeconds,
                )}
              </span>

              <button
                type="button"
                className="voice-recording-send"
                aria-label="Stop recording and send"
                title="Stop and send"
                onClick={() => {
                  void finishVoiceRecording(true)
                }}
              >
                <span
                  className="voice-recording-stop-icon"
                  aria-hidden="true"
                />
              </button>
            </div>
          ) : null}

          {selectedImage && selectedImagePreview && (
            <div className="attachment-preview">
              <img
                src={selectedImagePreview}
                alt=""
                className="attachment-preview-image"
              />

              <div className="attachment-preview-meta">
                <span title={selectedImage.name}>
                  {selectedImage.name}
                </span>
                <small>
                  {Math.max(
                    1,
                    Math.round(selectedImage.size / 1024),
                  )}{' '}
                  KB
                </small>
              </div>

              <button
                type="button"
                className="attachment-remove-button"
                aria-label="Remove selected image"
                title="Remove image"
                disabled={sending}
                onClick={clearSelectedImage}
              >
                ×
              </button>
            </div>
          )}

          <input
            ref={fileInputRef}
            className="attachment-file-input"
            type="file"
            accept="image/png,image/jpeg"
            aria-label="Choose an image"
            disabled={sending}
            onChange={handleImageSelected}
          />

          <button
            type="button"
            className="attachment-button"
            aria-label="Attach image"
            title="Attach image"
            disabled={sending}
            onClick={() => {
              fileInputRef.current?.click()
            }}
          >
            <span aria-hidden="true">+</span>
          </button>

          <textarea
            ref={composerRef}
            rows={1}
            placeholder="Message Corvus…"
            aria-label="Message Corvus"
            value={draft}
            disabled={sending}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                event.currentTarget.form?.requestSubmit()
              }
            }}
          />
          <button
            type="button"
            className="voice-mic-button"
            aria-label="Start voice recording"
            title="Voice message"
            disabled={
              sending ||
              recording ||
              Boolean(selectedImage)
            }
            onClick={() => {
              void startVoiceRecording()
            }}
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <rect
                x="9"
                y="3"
                width="6"
                height="11"
                rx="3"
              />
              <path d="M5.5 11a6.5 6.5 0 0 0 13 0" />
              <path d="M12 17.5V21" />
              <path d="M9 21h6" />
            </svg>
          </button>

          <button
            type="submit"
            className="send-button"
            disabled={sending || !draft.trim()}
            aria-label={sending ? 'Sending message' : 'Send message'}
          >
            {sending ? (
              <span className="send-spinner" />
            ) : (
              <span className="send-arrow">↑</span>
            )}
          </button>
        </form>
        {chatError && (
          <p className="chat-error" role="alert">
            {chatError}
          </p>
        )}
        </section>
      </div>

      {inspectOpen && (
        <button
          type="button"
          className="drawer-backdrop"
          aria-label="Close inspector"
          onClick={() => setInspectOpen(false)}
        />
      )}

      <aside className={`inspector ${inspectOpen ? 'open' : ''}`}>
        <header className="inspector-header">
          <div>
            <span className="eyebrow">MEMORY</span>
            <h2>Inspector</h2>
          </div>
        </header>

        <nav className="inspect-tabs">
          <button className={tab === 'evidence' ? 'active' : ''} onClick={() => setTab('evidence')}>Evidence</button>
          <button className={tab === 'assertions' ? 'active' : ''} onClick={() => setTab('assertions')}>Assertions</button>
          <button className={tab === 'world' ? 'active' : ''} onClick={() => setTab('world')}>World</button>
        </nav>

        <section className="inspector-content">
          {tab === 'evidence' && (
            <div className="evidence-list">
              {evidence.map((item) => (
                <article className="evidence-item" key={item.id}>
                  <div className="evidence-meta">
                    <span>#{item.id}</span>
                    <span>{item.role}</span>
                    <span>{item.session_id}</span>
                  </div>
                  <p>{item.content}</p>
                  <time>{item.created_at}</time>
                </article>
              ))}
            </div>
          )}
          {tab === 'assertions' && <p>Assertions</p>}
          {tab === 'world' && <p>Current World</p>}
        </section>
      </aside>
    </main>
  )
}

export default App

import { useState, useRef } from 'react'

const API_BASE = '/api'

function SpeakerIdentification({ result, sessionId, onConfirm, onSkip }) {
    // Build initial speaker list from diarization results
    const speakerStats = result.transcript.speaker_summary
    const speakerClips = result.speaker_clips || {}

    const speakers = Object.keys(speakerStats.speaking_time).sort()

    const [speakerNames, setSpeakerNames] = useState(
        speakers.reduce((acc, speaker) => {
            acc[speaker] = { name: '', position: '' }
            return acc
        }, {})
    )
    const [playingSpeaker, setPlayingSpeaker] = useState(null)
    const audioRef = useRef(null)

    const totalSpeakingTime = Object.values(speakerStats.speaking_time).reduce((a, b) => a + b, 0)

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    const updateSpeakerField = (speaker, field, value) => {
        setSpeakerNames(prev => ({
            ...prev,
            [speaker]: { ...prev[speaker], [field]: value }
        }))
    }

    const handlePlayClip = (speaker) => {
        const clip = speakerClips[speaker]
        if (!clip || !sessionId) return

        const clipUrl = `${API_BASE}/speaker-clip/${sessionId}/${clip.clip_filename}`

        if (playingSpeaker === speaker && audioRef.current) {
            audioRef.current.pause()
            audioRef.current.currentTime = 0
            setPlayingSpeaker(null)
            return
        }

        if (audioRef.current) {
            audioRef.current.pause()
        }

        const audio = new Audio(clipUrl)
        audioRef.current = audio
        setPlayingSpeaker(speaker)

        audio.play().catch(err => {
            console.error('Audio play error:', err)
            setPlayingSpeaker(null)
        })

        audio.onended = () => {
            setPlayingSpeaker(null)
        }
    }

    const handleConfirm = () => {
        // Build speaker mapping: { "คนพูด 1": "สมชาย (ผู้จัดการ)" }
        const mapping = {}
        for (const [speaker, info] of Object.entries(speakerNames)) {
            if (info.name.trim()) {
                mapping[speaker] = info.position.trim()
                    ? `${info.name.trim()} (${info.position.trim()})`
                    : info.name.trim()
            }
        }
        onConfirm(mapping)
    }

    const handleSkip = () => {
        onSkip()
    }

    const hasAnyName = Object.values(speakerNames).some(s => s.name.trim() !== '')

    return (
        <div className="speaker-id-panel">
            <div className="speaker-id-header">
                <h3 className="speaker-id-title">👥 ระบุตัวตนผู้เข้าร่วมประชุม</h3>
                <p className="speaker-id-subtitle">
                    พบผู้พูด <strong>{speakers.length}</strong> คนจากการวิเคราะห์เสียง
                    — ฟังเสียงตัวอย่างแล้วกรอกชื่อ
                </p>
            </div>

            <div className="speaker-id-list">
                {speakers.map((speaker, index) => {
                    const time = speakerStats.speaking_time[speaker] || 0
                    const pct = totalSpeakingTime > 0 ? (time / totalSpeakingTime) * 100 : 0
                    const wordCount = speakerStats.word_count[speaker] || 0
                    const clip = speakerClips[speaker]
                    const isPlaying = playingSpeaker === speaker

                    return (
                        <div key={speaker} className="speaker-id-card">
                            <div className="speaker-id-card-header">
                                <div className="speaker-id-avatar">
                                    {index + 1}
                                </div>
                                <div className="speaker-id-info">
                                    <span className="speaker-id-label">{speaker}</span>
                                    <span className="speaker-id-meta">
                                        🕐 {formatTime(time)} ({pct.toFixed(1)}%) • {wordCount} คำ
                                    </span>
                                </div>
                                {clip && (
                                    <button
                                        className={`btn-play-clip ${isPlaying ? 'playing' : ''}`}
                                        onClick={() => handlePlayClip(speaker)}
                                        title={isPlaying ? 'หยุดเล่น' : 'เล่นตัวอย่างเสียง'}
                                    >
                                        {isPlaying ? '⏹️ หยุด' : '▶️ ฟังเสียง'}
                                    </button>
                                )}
                            </div>

                            {clip && (
                                <div className="speaker-id-clip-info">
                                    🔊 ตัวอย่างเสียง {clip.duration.toFixed(1)} วินาที
                                    ({formatTime(clip.start)} - {formatTime(clip.end)})
                                </div>
                            )}

                            <div className="speaker-id-fields">
                                <input
                                    type="text"
                                    className="speaker-id-input"
                                    placeholder="ชื่อ-สกุล"
                                    value={speakerNames[speaker]?.name || ''}
                                    onChange={(e) => updateSpeakerField(speaker, 'name', e.target.value)}
                                />
                                <input
                                    type="text"
                                    className="speaker-id-input"
                                    placeholder="ตำแหน่ง"
                                    value={speakerNames[speaker]?.position || ''}
                                    onChange={(e) => updateSpeakerField(speaker, 'position', e.target.value)}
                                />
                            </div>

                            {/* Speaking time bar */}
                            <div className="speaker-id-bar-container">
                                <div
                                    className="speaker-id-bar-fill"
                                    style={{ width: `${pct}%` }}
                                />
                            </div>
                        </div>
                    )
                })}
            </div>

            <div className="speaker-id-actions">
                <button
                    className="btn btn-primary"
                    onClick={handleConfirm}
                    disabled={!hasAnyName}
                >
                    ✅ ยืนยันข้อมูลผู้เข้าร่วม
                </button>
                <button
                    className="btn btn-secondary"
                    onClick={handleSkip}
                >
                    ⏭️ ข้ามขั้นตอนนี้
                </button>
            </div>
        </div>
    )
}

export default SpeakerIdentification

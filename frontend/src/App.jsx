import { useState } from 'react'
import FileUploader from './components/FileUploader'
import MeetingTypeSelect from './components/MeetingTypeSelect'
import SpeakerIdentification from './components/SpeakerIdentification'
import ProcessingStatus from './components/ProcessingStatus'
import ResultsTabs from './components/ResultsTabs'

// API Base URL - uses proxy in dev, direct in production
const API_BASE = '/api'

function App() {
    const [file, setFile] = useState(null)
    const [meetingType, setMeetingType] = useState(0)
    const [isProcessing, setIsProcessing] = useState(false)
    const [currentStep, setCurrentStep] = useState(0)
    const [progress, setProgress] = useState(0)
    const [result, setResult] = useState(null)
    const [sessionId, setSessionId] = useState(null)
    const [speakerMapping, setSpeakerMapping] = useState(null)
    const [isNamingComplete, setIsNamingComplete] = useState(false)
    const [error, setError] = useState(null)

    const handleFileSelect = (selectedFile) => {
        setFile(selectedFile)
        setError(null)
        setResult(null)
        setSpeakerMapping(null)
        setIsNamingComplete(false)
        setSessionId(null)
    }

    const handleSubmit = async () => {
        if (!file) return

        setIsProcessing(true)
        setError(null)
        setResult(null)
        setSpeakerMapping(null)
        setIsNamingComplete(false)
        setCurrentStep(0)
        setProgress(0)

        // Simulate progress stages
        const progressSteps = [
            { step: 0, progress: 10, delay: 0 },      // Model Load start
            { step: 1, progress: 20, delay: 5000 },   // Audio Load
            { step: 2, progress: 40, delay: 8000 },   // Transcription
            { step: 3, progress: 70, delay: 30000 },  // Diarization
            { step: 4, progress: 90, delay: 50000 },  // Summarization
        ]

        const progressTimers = progressSteps.map(({ step, progress: prog, delay }) =>
            setTimeout(() => {
                setCurrentStep(step)
                setProgress(prog)
            }, delay)
        )

        try {
            const formData = new FormData()
            formData.append('audio', file)
            formData.append('meeting_type_id', meetingType)

            const response = await fetch(`${API_BASE}/transcribe-summarize`, {
                method: 'POST',
                body: formData,
            })

            // Clear progress timers
            progressTimers.forEach(timer => clearTimeout(timer))

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Processing failed')
            }

            const data = await response.json()
            setResult(data)
            setSessionId(data.session_id)
            setProgress(100)
            setCurrentStep(5)
        } catch (err) {
            setError(err.message || 'เกิดข้อผิดพลาดในการประมวลผล')
            progressTimers.forEach(timer => clearTimeout(timer))
        } finally {
            setIsProcessing(false)
        }
    }

    // Apply speaker name mapping to result (client-side replacement)
    const applyMapping = (mapping) => {
        setSpeakerMapping(mapping)
        setIsNamingComplete(true)
    }

    // Get display-ready result with mapped speaker names
    const getMappedResult = () => {
        if (!result) return null
        if (!speakerMapping || Object.keys(speakerMapping).length === 0) return result

        // Deep clone result
        const mapped = JSON.parse(JSON.stringify(result))

        // Replace speaker names in segments
        mapped.transcript.segments = mapped.transcript.segments.map(seg => ({
            ...seg,
            speaker: speakerMapping[seg.speaker] || seg.speaker
        }))

        // Replace speaker names in summary text
        let mappedSummary = mapped.summary
        for (const [generic, real] of Object.entries(speakerMapping)) {
            mappedSummary = mappedSummary.replaceAll(generic, real)
        }
        mapped.summary = mappedSummary

        // Replace speaker names in speaker_summary
        const newSpeakingTime = {}
        const newWordCount = {}
        for (const [speaker, time] of Object.entries(mapped.transcript.speaker_summary.speaking_time)) {
            const newName = speakerMapping[speaker] || speaker
            newSpeakingTime[newName] = time
        }
        for (const [speaker, count] of Object.entries(mapped.transcript.speaker_summary.word_count)) {
            const newName = speakerMapping[speaker] || speaker
            newWordCount[newName] = count
        }
        mapped.transcript.speaker_summary = {
            speaking_time: newSpeakingTime,
            word_count: newWordCount,
        }

        return mapped
    }

    const handleSpeakerConfirm = (mapping) => {
        applyMapping(mapping)
    }

    const handleSpeakerSkip = () => {
        setIsNamingComplete(true)
    }

    const displayResult = isNamingComplete ? getMappedResult() : null

    return (
        <div className="app-container">
            {/* Header */}
            <header className="header">
                <h1 className="header-title">🎙️ Timsum</h1>
                <p className="header-subtitle">ถอดเสียงประชุมและสรุปอัตโนมัติด้วย AI</p>
            </header>

            <main className="main-content">
                {/* Upload Section */}
                <section className="glass-card">
                    <FileUploader
                        file={file}
                        onFileSelect={handleFileSelect}
                        disabled={isProcessing}
                    />
                </section>

                {/* Meeting Type Selection */}
                <section className="glass-card">
                    <MeetingTypeSelect
                        value={meetingType}
                        onChange={setMeetingType}
                        disabled={isProcessing}
                    />

                    {/* Submit Button */}
                    <button
                        className="btn btn-primary btn-full"
                        onClick={handleSubmit}
                        disabled={!file || isProcessing}
                    >
                        {isProcessing ? '⏳ กำลังประมวลผล...' : '🚀 เริ่มประมวลผล'}
                    </button>
                </section>

                {/* Processing Status */}
                {isProcessing && (
                    <section className="glass-card">
                        <ProcessingStatus
                            currentStep={currentStep}
                            progress={progress}
                        />
                    </section>
                )}

                {/* Error Message */}
                {error && (
                    <div className="error-message">
                        <span>❌</span>
                        <span>{error}</span>
                    </div>
                )}

                {/* Speaker Identification (after processing, before showing results) */}
                {result && !isNamingComplete && (
                    <section className="glass-card">
                        <SpeakerIdentification
                            result={result}
                            sessionId={sessionId}
                            onConfirm={handleSpeakerConfirm}
                            onSkip={handleSpeakerSkip}
                        />
                    </section>
                )}

                {/* Results (after speaker naming is done) */}
                {displayResult && (
                    <section className="glass-card results-section">
                        <ResultsTabs result={displayResult} meetingType={meetingType} />
                    </section>
                )}
            </main>
        </div>
    )
}

export default App

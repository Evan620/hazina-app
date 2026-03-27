/**
 * Document Upload Component
 * Reusable document upload with drag-and-drop support for the Listing Scanner.
 */

import React, { useState, useRef } from "react";

// Shared colors from HazinaDemo.tsx
const C = {
  border: "rgba(255,255,255,0.1)",
  text: "#ffffff",
  textDim: "rgba(255,255,255,0.6)",
  textMuted: "rgba(255,255,255,0.4)",
  bg: "#0a0e1a",
  cardAlt: "rgba(255,255,255,0.03)",
  accent: "#3b82f6",
  success: "#10b981",
  error: "#ef4444",
  warning: "#f59e0b"
};

interface DocumentUploadProps {
  documentType: string;
  label: string;
  description: string;
  accept: string;
  onUpload: (file: File, documentType: string) => void;
  onRemove: (documentType: string) => void;
  uploadedFile?: File;
  isUploading?: boolean;
  maxSize?: number; // Max file size in MB (default: 10)
}

export default function DocumentUpload({
  documentType,
  label,
  description,
  accept,
  onUpload,
  onRemove,
  uploadedFile,
  isUploading = false,
  maxSize = 10
}: DocumentUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): boolean => {
    setError(null);

    // Check file size
    if (file.size > maxSize * 1024 * 1024) {
      setError(`File too large. Max ${maxSize}MB.`);
      return false;
    }

    // Check file type
    const acceptedTypes = accept.split(",").map(t => t.trim());
    const fileExtension = "." + file.name.split(".").pop()?.toLowerCase();

    if (!acceptedTypes.some(t => {
      if (t.startsWith(".")) {
        return fileExtension === t.toLowerCase();
      } else if (t.includes("/*")) {
        const baseType = t.split("/*")[0];
        return file.type.startsWith(baseType);
      }
      return file.type === t;
    })) {
      setError(`Invalid file type. Accepted: ${accept}`);
      return false;
    }

    return true;
  };

  const handleFile = (file: File) => {
    if (validateFile(file)) {
      onUpload(file, documentType);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRemove(documentType);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    setError(null);
  };

  return (
    <div
      style={{
        border: `1px dashed ${dragOver ? C.accent : error ? C.error : C.border}`,
        borderRadius: 8,
        padding: 16,
        background: dragOver ? "rgba(59, 130, 246, 0.1)" : "transparent",
        transition: "all 0.2s ease",
        cursor: uploadedFile ? "default" : "pointer"
      }}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={uploadedFile ? undefined : handleClick}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileInputChange}
        style={{ display: "none" }}
      />

      {/* Header */}
      <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 6, color: C.text }}>
        {label}
      </div>

      {/* Description */}
      {!uploadedFile && (
        <div style={{ fontSize: 10, color: C.textMuted, marginBottom: 8 }}>
          {description}
        </div>
      )}

      {/* Upload Area / File Preview */}
      {uploadedFile ? (
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 20 }}>📄</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 11, color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {uploadedFile.name}
            </div>
            <div style={{ fontSize: 9, color: C.textMuted }}>
              {(uploadedFile.size / 1024).toFixed(1)} KB
            </div>
          </div>
          <button
            onClick={handleRemove}
            disabled={isUploading}
            style={{
              background: C.error,
              border: "none",
              borderRadius: 4,
              width: 24,
              height: 24,
              cursor: isUploading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
              fontSize: 14,
              opacity: isUploading ? 0.5 : 1
            }}
            title="Remove file"
          >
            ×
          </button>
        </div>
      ) : isUploading ? (
        <div style={{ textAlign: "center", padding: 16 }}>
          <div style={{ fontSize: 10, color: C.textDim }}>Uploading...</div>
        </div>
      ) : (
        <div
          style={{
            textAlign: "center",
            padding: "20px 16px",
            border: `1px dashed ${C.border}`,
            borderRadius: 6,
            background: C.cardAlt
          }}
        >
          <div style={{ fontSize: 20, marginBottom: 8 }}>📎</div>
          <div style={{ fontSize: 10, color: C.textDim }}>
            Click to upload or drag & drop
          </div>
          <div style={{ fontSize: 9, color: C.textMuted, marginTop: 4 }}>
            Max {maxSize}MB • {accept}
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div style={{ fontSize: 9, color: C.error, marginTop: 8 }}>
          ⚠️ {error}
        </div>
      )}
    </div>
  );
}

/**
 * ManualVerificationInput Component
 * For entering verification codes manually as an alternative to document upload.
 */
interface ManualVerificationInputProps {
  auditorContact: string;
  kraPin: string;
  crdReference: string;
  onChange: (field: "auditor_contact" | "kra_pin" | "crd_reference", value: string) => void;
}

export function ManualVerificationInput({
  auditorContact,
  kraPin,
  crdReference,
  onChange
}: ManualVerificationInputProps) {
  const inputStyle = {
    width: "100%",
    padding: "10px 12px",
    background: C.cardAlt,
    border: `1px solid ${C.border}`,
    borderRadius: 6,
    color: C.text,
    fontSize: 11,
    outline: "none",
    transition: "border-color 0.2s ease"
  };

  const labelStyle = {
    fontSize: 10,
    fontWeight: 500,
    color: C.textDim,
    marginBottom: 4
  };

  return (
    <div style={{
      marginTop: 16,
      paddingTop: 16,
      borderTop: `1px solid ${C.border}`
    }}>
      <div style={{ fontSize: 11, color: C.textDim, marginBottom: 12 }}>
        Or enter verification details manually:
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        <div>
          <div style={labelStyle}>Auditor Email/Phone</div>
          <input
            type="text"
            placeholder="auditor@firm.com"
            value={auditorContact}
            onChange={(e) => onChange("auditor_contact", e.target.value)}
            style={inputStyle}
          />
        </div>

        <div>
          <div style={labelStyle}>KRA Tax PIN</div>
          <input
            type="text"
            placeholder="A00xxxxxxxx"
            value={kraPin}
            onChange={(e) => onChange("kra_pin", e.target.value)}
            style={inputStyle}
            maxLength={11}
          />
        </div>

        <div>
          <div style={labelStyle}>CRD Reference #</div>
          <input
            type="text"
            placeholder="CRD-XXXXXX"
            value={crdReference}
            onChange={(e) => onChange("crd_reference", e.target.value)}
            style={inputStyle}
          />
        </div>
      </div>

      <div style={{ fontSize: 9, color: C.textMuted, marginTop: 8 }}>
        These codes will be validated for format. Real verification requires document upload.
      </div>
    </div>
  );
}

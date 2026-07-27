import React from 'react';

interface ModalProps {
  title?: string;
  children: React.ReactNode;
  onClose: () => void;
  /** Optional label for a confirm button. If provided, a confirm button is shown alongside a cancel button. */
  confirmLabel?: string;
  /** Called when confirm button is clicked. */
  onConfirm?: () => void;
}

/**
 * Generic modal component that matches the existing dark theme of the app.
 * It uses Tailwind CSS classes to style the overlay and dialog.
 */
const Modal: React.FC<ModalProps> = ({ title, children, onClose, confirmLabel, onConfirm }) => {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-60 z-50">
      <div className="bg-slate-800 text-gray-200 rounded-lg p-6 w-96 max-w-full shadow-lg">
        {title && (
          <h2 className="text-lg font-semibold mb-4 border-b border-slate-600 pb-2">{title}</h2>
        )}
        <div className="mb-4">{children}</div>
        <div className="flex justify-end space-x-2">
          <button
            onClick={onClose}
            className="px-3 py-1 text-sm font-medium text-gray-300 bg-slate-700 rounded hover:bg-slate-600"
          >
            {confirmLabel ? 'Cancel' : 'Close'}
          </button>
          {confirmLabel && onConfirm && (
            <button
              onClick={onConfirm}
              className="px-3 py-1 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-500"
            >
              {confirmLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default Modal;

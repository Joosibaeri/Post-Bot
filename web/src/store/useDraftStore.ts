import { create } from 'zustand';
import { PostContext } from '@/types/dashboard';

interface DraftState {
  // Post Generation State
  context: PostContext;
  preview: string;
  isEditing: boolean;
  loading: boolean;
  status: string;
  selectedImage: string | null;

  // Actions
  setContext: (contextOrUpdater: PostContext | ((prev: PostContext) => PostContext)) => void;
  setPreview: (preview: string) => void;
  setIsEditing: (isEditing: boolean) => void;
  setLoading: (loading: boolean) => void;
  setStatus: (status: string) => void;
  setSelectedImage: (image: string | null) => void;
  reset: () => void;
}

const initialContext: PostContext = {
  type: 'push',
  commits: 3,
  repo: 'my-project',
  full_repo: 'username/my-project',
  date: '2 hours ago',
};

export const useDraftStore = create<DraftState>((set) => ({
  context: initialContext,
  preview: '',
  isEditing: false,
  loading: false,
  status: '',
  selectedImage: null,

  setContext: (contextOrUpdater) => set((state) => ({
    context: typeof contextOrUpdater === 'function' ? contextOrUpdater(state.context) : contextOrUpdater
  })),
  setPreview: (preview) => set({ preview }),
  setIsEditing: (isEditing) => set({ isEditing }),
  setLoading: (loading) => set({ loading }),
  setStatus: (status) => set({ status }),
  setSelectedImage: (selectedImage) => set({ selectedImage }),
  reset: () => set({
    context: initialContext,
    preview: '',
    isEditing: false,
    loading: false,
    status: '',
    selectedImage: null,
  })
}));
